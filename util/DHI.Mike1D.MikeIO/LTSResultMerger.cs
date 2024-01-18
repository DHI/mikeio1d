using System;
using System.Collections.Generic;
using System.Linq;
using DHI.Generic.MikeZero;
using DHI.Mike1D.Generic;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Class for merging Long Term Statistics (LTS) result files.
  /// </summary>
  public abstract class LTSResultMerger
  {
    /// <summary>
    /// Instances of ResultData which will be merged.
    /// </summary>
    protected IList<ResultData> _resultDataCollection;

    /// <summary>
    /// Result data, where the merged results will be stored.
    /// </summary>
    protected ResultData _resultData;

    /// <summary>
    /// Data entries corresponding to the <see cref="_resultData"/>.
    /// </summary>
    protected List<DataEntry> _dataEntries;

    /// <summary>
    /// Map from data entry ID to actual data entry.
    /// </summary>
    protected Dictionary<DataEntryId, DataEntry> _mapIdToDataEntry;

    /// <summary>
    /// Map from data entry ID to list of LTS result events.
    /// </summary>
    protected Dictionary<DataEntryId, LTSResultEvents> _mapIdToResultEvents;

    /// <inheritdoc cref="LTSResultMerger" />
    public LTSResultMerger(IList<ResultData> resultDataCollection)
    {
      _resultDataCollection = resultDataCollection;
      _resultData = _resultDataCollection.First();
      _dataEntries = _resultData.GetAllDataEntries();
    }

    /// <summary>
    /// Create particular LTSResultMerger class depending on the result type.
    /// </summary>
    public static LTSResultMerger Create(IList<ResultData> resultDataCollection)
    {
      var resultData = resultDataCollection.FirstOrDefault();
      if (resultData == null)
        throw new Exception("Empty result data list provided.");

      var resultType = resultData.ResultType;
      switch (resultType)
      {
        case ResultTypes.LTSEvents:
          return new LTSResultMergerExtreme(resultDataCollection);

        case ResultTypes.LTSAnnual:
        case ResultTypes.LTSMonthly:
          return new LTSResultMergerPeriodic(resultDataCollection);
        default:
          throw new NotSupportedException($"Not supported result type {resultType}");
      }
    }

    #region Static Merge methods

    /// <summary>
    /// Merge result files given by their file names
    /// </summary>
    public static ResultData Merge(IList<string> resultFileNames)
    {
      var resultFilePaths = resultFileNames.Select(name => new FilePath(name)).ToList();
      return Merge(resultFilePaths);
    }

    /// <summary>
    /// Merge result files given by their FilePath specification.
    /// </summary>
    public static ResultData Merge(IList<FilePath> resultFilePaths)
    {
      var resultData = resultFilePaths.Select(path => LoadFile(path.FullFilePath)).ToList();
      return Merge(resultData);
    }

    /// <summary>
    /// Merge result files given by their ResultData specification.
    /// </summary>
    public static ResultData Merge(IList<ResultData> resultDataCollection)
    {
      var merger = LTSResultMerger.Create(resultDataCollection);
      return merger.Merge();
    }

    /// <summary>
    /// Loads a file based on the filename.
    /// </summary>
    private static ResultData LoadFile(string fileName)
    {
      var res = new ResultData();
      res.Connection = Connection.Create(fileName);

      var diagnostics = new Diagnostics("LTS result merging");
      res.Load(diagnostics);

      return res;
    }

    #endregion Static Merge methods

    /// <summary>
    /// Performs the actual merging of result files.
    /// </summary>
    public ResultData Merge()
    {
      CreateMaps();
      MergeDataEntries();
      SortResults();
      ProcessResults();
      UpdateTimesList();
      UpdateResultData();

      return _resultData;
    }

    #region CreateMaps

    private void CreateMaps()
    {
      _mapIdToDataEntry = CreateMapIdToDataEntry(_dataEntries);
      _mapIdToResultEvents = CreateMapIdToResultEvents(_dataEntries);
    }

    private static Dictionary<DataEntryId, DataEntry> CreateMapIdToDataEntry(List<DataEntry> dataEntries)
    {
      var mapIdToDataEntry = dataEntries.ToDictionary(dataEntry => dataEntry.EntryId);
      return mapIdToDataEntry;
    }

    private static Dictionary<DataEntryId, LTSResultEvents> CreateMapIdToResultEvents(List<DataEntry> dataEntries)
    {
      var mapIdToResultEvents = dataEntries.ToDictionary(dataEntry => dataEntry.EntryId, dataEntry => new LTSResultEvents());
      return mapIdToResultEvents;
    }

    #endregion CreateMaps

    #region MergeDataEntries

    /// <summary>
    /// Merges data entries, which means that the full LTS event result list
    /// is created from all the specified res1d files.
    /// </summary>
    protected void MergeDataEntries()
    {
      foreach (var resultData in _resultDataCollection)
      {
        var dataEntries = resultData.GetAllDataEntries();
        var mapIdToDataEntry = CreateMapIdToDataEntry(dataEntries);
        foreach (var dataEntry in dataEntries)
          MergeDataEntry(dataEntry, mapIdToDataEntry, resultData);
      }
    }

    /// <summary>
    /// Merge in a particular DataEntry.
    /// </summary>
    /// <param name="dataEntry">The DataEntry to merge in</param>
    /// <param name="mapIdToDataEntry">A map from DataEntryId to DataEntry used for finding DataEntry for derived quantity</param>
    /// <param name="resultData">ResultData where DataEntry comes from</param>
    protected abstract void MergeDataEntry(
        DataEntry dataEntry,
        Dictionary<DataEntryId, DataEntry> mapIdToDataEntry,
        ResultData resultData);

    /// <summary>
    /// Check if the quantity is a derived LTS quantity.
    /// <para>
    /// For example, derived LTS quantity is the time of the event
    /// and for extreme statistics we have (derived quantity ID on the right):
    ///   DischargeMaximum - DischargeMaximumTime
    /// For periodic statistics we have as an example:
    ///   DischargeIntegratedMonthly - DischargeIntegratedMonthlyCount
    ///   DischargeIntegratedMonthly - DischargeIntegratedMonthlyDuration
    /// </para>
    /// </summary>
    protected abstract bool IsDerivedQuantity(IQuantity quantity);

    /// <summary>
    /// Get the DataEntry of a derived quantity.
    /// </summary>
    /// <param name="extraId">Extra ID string defining the derived quantity</param>
    /// <param name="dataEntry">DataEntry corresponding to original LTS quantity</param>
    /// <param name="mapIdToDataEntry">A map from DataEntryId to DataEntry</param>
    /// <returns>DataEntry for derived quantity</returns>
    public static DataEntry GetDataEntryForDerivedQuantity(string extraId, DataEntry dataEntry, Dictionary<DataEntryId, DataEntry> mapIdToDataEntry)
    {
      var quantity = dataEntry.DataItem.Quantity;
      var quantityTime = Create(quantity, extraId);
      var entryId = dataEntry.EntryId;
      var entryIdDerived = new DataEntryId(quantityTime.Id, entryId);
      var dataEntryDerived = mapIdToDataEntry[entryIdDerived];
      return dataEntryDerived;
    }

    /// <summary>
    /// Create a quantity with "extra" string added to Id and description.
    /// </summary>
    public static IQuantity Create(IQuantity quantity, string extra, eumItem item = eumItem.eumITimeScale, eumUnit? unit = null)
    {
      var ex = new ExtraForQuantities(extra);
      string id = quantity.Id + ex.ExtraForId;
      string description = quantity.Description + ex.ExtraForDescription;

      var extraQuantity = unit == null
        ? new Quantity(id, description, item)
        : new Quantity(id, description, item, unit.Value);

      return extraQuantity;
    }

    #endregion

    /// <summary>
    /// Sort LTSResultEvents on value or time inside <see cref="_mapIdToDataEntry"/>
    /// </summary>
    protected abstract void SortResults();

    /// <summary>
    /// Apply processing on LTSResultEvents inside <see cref="_mapIdToDataEntry"/>
    /// </summary>
    protected abstract void ProcessResults();

    /// <summary>
    /// Create a new ResultData.TimesList for merged <see cref="_resultData"/>
    /// </summary>
    protected abstract void UpdateTimesList();

    /// <summary>
    /// Update <see cref="_resultData"/> with actual merged LTS data.
    /// </summary>
    protected abstract void UpdateResultData();
  }
}

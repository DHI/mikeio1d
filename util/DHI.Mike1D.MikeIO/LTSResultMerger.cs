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
  public abstract class LTSResultMerger : ResultMerger
  {
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
    public LTSResultMerger(IList<ResultData> resultDataCollection) : base(resultDataCollection)
    {
      LoadData();
      _dataEntries = _resultData.GetAllDataEntries();
    }

    private void LoadData()
    {
      var diagnostics = new Diagnostics("LTS result merging");
      foreach (var resultData in _resultDataCollection)
        if (resultData.LoadStatus == LoadStatus.Header)
          resultData.LoadData(diagnostics);
    }

    /// <inheritdoc />
    public override ResultData Merge(string mergedFileName = null)
    {
      CreateMaps();
      MergeDataEntries();
      SortResults();
      ProcessResults();
      UpdateTimesList();
      UpdateResultData();
      SaveToFile(mergedFileName);

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
    protected virtual void SortResults()
    {
      _mapIdToResultEvents.Values.ToList().ForEach(x => x.Sort());
    }

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

    /// <summary>
    /// Save the current <see cref="_resultData"/> to a given file.
    /// </summary>
    /// <param name="mergedFileName">File name to save to.</param>
    public virtual void SaveToFile(string mergedFileName = null)
    {
      if (string.IsNullOrWhiteSpace(mergedFileName))
        return;

      _resultData.Connection.FilePath.Path = mergedFileName;
      _resultData.Save();
    }
  }
}

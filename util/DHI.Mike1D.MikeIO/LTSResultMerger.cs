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
  public class LTSResultMerger
  {
    /// <summary>
    /// Instances of ResultData which will be merged.
    /// </summary>
    private IList<ResultData> _resultDataCollection;

    /// <summary>
    /// Result data, where the merged results will be stored.
    /// </summary>
    private ResultData _resultData;

    /// <summary>
    /// Data entries corresponding to the <see cref="_resultData"/>.
    /// </summary>
    private List<DataEntry> _dataEntries;

    /// <summary>
    /// Map from data entry ID to actual data entry.
    /// </summary>
    private Dictionary<DataEntryId, DataEntry> _mapIdToDataEntry;

    /// <summary>
    /// Map from data entry ID to list of LTS result events.
    /// </summary>
    private Dictionary<DataEntryId, LTSResultEvents> _mapIdToResultEvents;

    /// <inheritdoc cref="LTSResultMerger" />
    public LTSResultMerger(IList<ResultData> resultDataCollection)
    {
      _resultDataCollection = resultDataCollection;
      _resultData = _resultDataCollection.First();
      _dataEntries = _resultData.GetAllDataEntries();
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
      var merger = new LTSResultMerger(resultDataCollection);
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
      SortResultEvents();
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
    private void MergeDataEntries()
    {
      foreach (var resultData in _resultDataCollection)
      {
        var dataEntries = resultData.GetAllDataEntries();
        var mapIdToDataEntry = CreateMapIdToDataEntry(dataEntries);
        foreach (var dataEntry in dataEntries)
          MergeDataEntry(dataEntry, mapIdToDataEntry);
      }
    }

    private void MergeDataEntry(DataEntry dataEntry, Dictionary<DataEntryId, DataEntry> mapIdToDataEntry)
    {
      var dataItem = dataEntry.DataItem;
      bool isTimeQuantity = dataItem.Quantity.Description.Contains(", Time");
      if (isTimeQuantity)
        return;

      var dataEntryTime = GetDataEntryForTimeQuantity(dataEntry, mapIdToDataEntry);
      var dataItemTime = dataEntryTime.DataItem;
      // TODO: Consider if the case of no Time quantity should be included
      if (dataItemTime == null)
        return;

      var ltsResultEvents = _mapIdToResultEvents[dataEntry.EntryId];
      int elementIndex = dataEntry.ElementIndex;
      for (int j = 0; j < dataItem.NumberOfTimeSteps; j++)
      {

        var ltsResultEvent = new LTSResultEvent
        {
          Value = dataItem.GetValue(j, elementIndex),
          Time = dataItemTime.GetValue(j, elementIndex)
        };
        ltsResultEvents.Add(ltsResultEvent);
      }
    }

    private static DataEntry GetDataEntryForTimeQuantity(DataEntry dataEntry, Dictionary<DataEntryId, DataEntry> mapIdToDataEntry)
    {
      var quantity = dataEntry.DataItem.Quantity;
      var quantityTime = Create(quantity, "Time");
      var entryId = dataEntry.EntryId;
      var entryIdTime = new DataEntryId(quantityTime.Id, entryId);
      var dataEntryTime = mapIdToDataEntry[entryIdTime];
      return dataEntryTime;
    }

    /// <summary>
    /// Create a quantity with "extra" string added to Id and description.
    /// </summary>
    private static IQuantity Create(IQuantity quantity, string extra, eumItem item = eumItem.eumITimeScale, eumUnit? unit = null)
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

    private void SortResultEvents()
    {
      _mapIdToResultEvents.Values.ToList().ForEach(x => x.SortOnValue());
    }

    #region UpdateTimesList

    private void UpdateTimesList()
    {
      var numberOfEventsEnumerable = _mapIdToResultEvents.Values.ToList().Select(x => x.Count);
      int largestNumberOfEvents = numberOfEventsEnumerable.Max();
      _resultData.TimesList = GetTimesListForEventResults(largestNumberOfEvents);
    }

    private static IListDateTimes GetTimesListForEventResults(int largestNumberOfEvents)
    {
      var timesList = new ListDateTimes();
      var startLabel = new DateTime(100, 1, 1);
      for (int i = 0; i < largestNumberOfEvents; i++)
      {
        var eventLabel = startLabel.AddSeconds(i);
        timesList.Add(eventLabel);
      }
      return timesList;
    }

    #endregion UpdateTimesList

    private void UpdateResultData()
    {
      foreach (var mapIdToResultEvent in _mapIdToResultEvents)
      {
        var entryId = mapIdToResultEvent.Key;
        var ltsResultEvents = mapIdToResultEvent.Value;
        if (ltsResultEvents.Count == 0)
          continue;

        var dataEntry = _mapIdToDataEntry[entryId];
        var dataEntryTime = GetDataEntryForTimeQuantity(dataEntry, _mapIdToDataEntry);

        for (int i = 0; i < ltsResultEvents.Count; i++)
        {
          var ltsResultEvent = ltsResultEvents[i];
          dataEntry.SetValue(i, ltsResultEvent.Value);
          dataEntryTime.SetValue(i, ltsResultEvent.Time);
        }
      }
    }
  }
}

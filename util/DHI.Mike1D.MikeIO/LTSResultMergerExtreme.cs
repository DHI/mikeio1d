using System;
using System.Collections.Generic;
using System.Linq;
using DHI.Mike1D.Generic;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Class for merging Long Term Statistics (LTS) extreme result files.
  /// </summary>
  public class LTSResultMergerExtreme : LTSResultMerger
  {
    /// <inheritdoc />
    public LTSResultMergerExtreme(IList<ResultData> resultDataCollection) : base(resultDataCollection)
    {
    }

    #region MergeDataEntries

    /// <inheritdoc />
    protected override void MergeDataEntry(
        DataEntry dataEntry,
        Dictionary<DataEntryId, DataEntry> mapIdToDataEntry,
        ResultData resultData)
    {
      var dataItem = dataEntry.DataItem;
      bool isDerivedQuantity = IsDerivedQuantity(dataItem.Quantity);
      if (isDerivedQuantity)
        return;

      var dataEntryTime = GetDataEntryForDerivedQuantity("Time", dataEntry, mapIdToDataEntry);
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

    /// <inheritdoc />
    protected override bool IsDerivedQuantity(IQuantity quantity)
    {
      bool isTimeQuantity = quantity.Description.Contains(", Time");
      if (isTimeQuantity)
        return true;

      return false;
    }

    #endregion

    /// <inheritdoc />
    protected override void ProcessResults()
    {
    }

    #region UpdateTimesList

    /// <inheritdoc />
    protected override void UpdateTimesList()
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

    /// <inheritdoc />
    protected override void UpdateResultData()
    {
      foreach (var mapIdToResultEvent in _mapIdToResultEvents)
      {
        var entryId = mapIdToResultEvent.Key;
        var ltsResultEvents = mapIdToResultEvent.Value;
        if (ltsResultEvents.Count == 0)
          continue;

        var dataEntry = _mapIdToDataEntry[entryId];
        var dataEntryTime = GetDataEntryForDerivedQuantity("Time", dataEntry, _mapIdToDataEntry);

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

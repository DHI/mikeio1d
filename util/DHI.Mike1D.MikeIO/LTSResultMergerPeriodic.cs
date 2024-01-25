using System.Collections.Generic;
using System.Linq;
using DHI.Mike1D.Generic;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Class for merging Long Term Statistics (LTS) periodic result files.
  /// </summary>
  public class LTSResultMergerPeriodic : LTSResultMerger
  {
    /// <inheritdoc />
    public LTSResultMergerPeriodic(IList<ResultData> resultDataCollection) : base(resultDataCollection)
    {
    }

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

      bool isGlobal = dataItem.ItemTypeGroup == ItemTypeGroup.GlobalItem;
      var dataItemCount = isGlobal ? null : GetDataEntryForDerivedQuantity("Count", dataEntry, mapIdToDataEntry).DataItem;
      var dataItemDuration = isGlobal ? null : GetDataEntryForDerivedQuantity("Duration", dataEntry, mapIdToDataEntry).DataItem;
      if ((dataItemCount == null || dataItemDuration == null) && !isGlobal)
        return;

      var ltsResultEventsPeriodic = _mapIdToResultEvents[dataEntry.EntryId];
      int elementIndex = dataEntry.ElementIndex;
      for (int j = 0; j < dataItem.NumberOfTimeSteps; j++)
      {
        var ltsResultEvent = new LTSResultEventPeriodic
        {
          Value = dataItem.GetValue(j, elementIndex),
          Count = (int)(dataItemCount?.GetValue(j, elementIndex) ?? 0),
          Duration = dataItemDuration?.GetValue(j, elementIndex) ?? 0.0,
          TimePeriod = resultData.TimesList[j]
        };
        ltsResultEventsPeriodic.Add(ltsResultEvent);
      }
    }

    /// <inheritdoc />
    protected override bool IsDerivedQuantity(IQuantity quantity)
    {
      if (quantity.Description.Contains(", Count"))
        return true;

      if (quantity.Description.Contains(", Duration"))
        return true;

      return false;
    }

    /// <inheritdoc />
    protected override void ProcessResults()
    {
      foreach (var mapIdToResultEvent in _mapIdToResultEvents)
      {
        var ltsResultEvents = mapIdToResultEvent.Value;
        for (int i = ltsResultEvents.Count - 1; i >= 1; i--)
        {
          var ltsResultEventAfter = (LTSResultEventPeriodic)ltsResultEvents[i];
          var ltsResultEventBefore = (LTSResultEventPeriodic)ltsResultEvents[i-1];
          if (ltsResultEventAfter.TimePeriod == ltsResultEventBefore.TimePeriod)
          {
            ltsResultEventBefore.Value += ltsResultEventAfter.Value;
            ltsResultEventBefore.Count += ltsResultEventAfter.Count;
            ltsResultEventBefore.Duration += ltsResultEventAfter.Duration;
            ltsResultEvents.RemoveAt(i);
          }
        }
      }
    }

    /// <inheritdoc />
    protected override void UpdateTimesList()
    {
      var ltsResultEventsPeriodic = _mapIdToResultEvents.Values.ToList().FirstOrDefault(x => x.Count > 0);
      if (ltsResultEventsPeriodic == null)
        return;

      var timesList = new ListDateTimes();
      foreach (var ltsResultEvent in ltsResultEventsPeriodic)
      {
        var ltsResultEventPeriodic = (LTSResultEventPeriodic)ltsResultEvent;
        timesList.Add(ltsResultEventPeriodic.TimePeriod);
      }

      _resultData.TimesList = timesList;
    }

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
        bool isGlobal = dataEntry.DataItem.ItemTypeGroup == ItemTypeGroup.GlobalItem;
        var dataEntryCount = isGlobal ? null : GetDataEntryForDerivedQuantity("Count", dataEntry, _mapIdToDataEntry);
        var dataEntryDuration = isGlobal ? null : GetDataEntryForDerivedQuantity("Duration", dataEntry, _mapIdToDataEntry);

        for (int i = 0; i < ltsResultEvents.Count; i++)
        {
          var ltsResultEventPeriodic = (LTSResultEventPeriodic)ltsResultEvents[i];
          dataEntry.SetValue(i, ltsResultEventPeriodic.Value);
          dataEntryCount?.SetValue(i, ltsResultEventPeriodic.Count);
          dataEntryDuration?.SetValue(i, ltsResultEventPeriodic.Duration);
        }
      }
    }
  }
}

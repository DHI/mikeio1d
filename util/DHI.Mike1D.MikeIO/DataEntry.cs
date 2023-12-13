using System;
using DHI.Mike1D.Generic;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Helper class, which contains a reference to a data item and an element index.
  /// </summary>
  public class DataEntry
  {
    public DataEntryId EntryId { get; set; }

    /// <inheritdoc cref="IDataItem"/>
    public IDataItem DataItem { get; set; }

    /// <summary>
    /// Element index into a data item.
    /// </summary>
    public int ElementIndex { get; set; }

    /// <inheritdoc cref="DataEntry" />
    public DataEntry(IDataItem dataItem, int elementIndex)
    {
      DataItem = dataItem;
      ElementIndex = elementIndex;
      EntryId = new DataEntryId(
        dataItem.Quantity.Id,
        dataItem.ItemTypeGroup,
        dataItem.NumberWithinGroup,
        ElementIndex);
    }

    /// <summary>
    /// Sets value for the data entry at a given time step index.
    /// <para>
    /// The data item time data is expanded if the index larger than
    /// the number of time steps.
    /// </para>
    /// </summary>
    public void SetValue(int timeStepIndex, double value)
    {
      int numberOfTimeSteps = DataItem.TimeData.NumberOfTimeSteps;
      if (numberOfTimeSteps <= timeStepIndex)
        ExpandTimeData(timeStepIndex - numberOfTimeSteps + 1);

      DataItem.TimeData.SetValue(timeStepIndex, ElementIndex, (float) value);
    }

    /// <summary>
    /// Expands time data by given expansion size.
    /// </summary>
    public void ExpandTimeData(int expansionSize = 1)
    {
      var elementDeleteValues = new float[DataItem.NumberOfElements];
      for (int i = 0; i < DataItem.NumberOfElements; i++)
        elementDeleteValues[i] = (float) Constants.DOUBLE_DELETE_VALUE;

      for (int i = 0; i < expansionSize; i++)
        DataItem.TimeData.Add(elementDeleteValues);
    }
  }

  /// <summary>
  /// Tuple ID for a DataEntry
  /// </summary>
  public class DataEntryId : Tuple<string, ItemTypeGroup, int, int>
  {
    /// <inheritdoc cref="DataEntryId" />
    public DataEntryId(
        string quantityId,
        ItemTypeGroup itemTypeGroup,
        int numberWithinGroup,
        int elementIndex) : base(quantityId, itemTypeGroup, numberWithinGroup, elementIndex)
    {
    }

    /// <inheritdoc cref="DataEntryId" />
    public DataEntryId(
      string quantityId,
      DataEntryId entryId) : base(quantityId, entryId.Item2, entryId.Item3, entryId.Item4)
    {
    }
  }
}

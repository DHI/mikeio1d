using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Helper class, which contains a reference to a data item and an element index.
  /// </summary>
  public class DataEntry
  {
    /// <inheritdoc cref="IDataItem"/>
    public IDataItem DataItem { get; set; }

    /// <summary>
    /// Element index into a data item.
    /// </summary>
    public int ElementIndex { get; set; }

    /// <inheritdoc />
    public DataEntry(IDataItem dataItem, int elementIndex)
    {
      DataItem = dataItem;
      ElementIndex = elementIndex;
    }
  }
}

using System.Collections.Generic;
using System.Linq;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Extension methods for ResultData.
  /// </summary>
  public static class ResultDataExtensions
  {
    /// <summary>
    /// Creates a list of all data entries corresponding to all data items.
    /// </summary>
    public static List<DataEntry> GetAllDataEntries(this ResultData resultData)
    {
      var dataEntries = resultData.DataSets
        .SelectMany(dataSet => dataSet.DataItems)
        .SelectMany(dataItem => Enumerable.Range(0, dataItem.NumberOfElements)
        .Select(elementIndex => new DataEntry(dataItem, elementIndex)))
        .ToList();
      return dataEntries;
    }
  }
}

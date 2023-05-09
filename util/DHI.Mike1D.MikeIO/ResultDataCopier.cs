using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Class which copies in the result data time series into
  /// an allocated memory specified by a pointer.
  /// </summary>
  public class ResultDataCopier
  {
    /// <summary>
    /// Instance of ResultData object to work with.
    /// </summary>
    public ResultData ResultData { get => _resultData; set => _resultData = value; }
    private ResultData _resultData;

    /// <inheritdoc />
    public ResultDataCopier(ResultData resultData)
    {
      _resultData = resultData;
    }

    /// <summary>
    /// Creates and empty list for DataEntry objects.
    /// </summary>
    public List<DataEntry> GetEmptyDataEntriesList()
    {
      return new List<DataEntry>();
    }

    /// <summary>
    /// Copies all the ResultData data items into memory specified by a given pointer.
    /// </summary
    public void CopyData(IntPtr intPointer)
    {
      var dataEntries = GetAllDataEntries();
      CopyData(intPointer, dataEntries);
    }

    /// <summary>
    /// Creates a list of all data entries corresponding to all data items.
    /// </summary
    public List<DataEntry> GetAllDataEntries()
    {
      var dataEntries = new List<DataEntry>();
      foreach (var dataSet in _resultData.DataSets)
      {
        foreach (var dataItem in dataSet.DataItems)
        {
          for (int i = 0; i < dataItem.NumberOfElements; i++)
          {
            var dataEntry = new DataEntry(dataItem, i);
            dataEntries.Add(dataEntry);
          }
        }
      }
      return dataEntries;
    }

    /// <summary>
    /// Copies the given data entries into memory specified by a pointer.
    /// </summary
    public void CopyData(IntPtr intPointer, List<DataEntry> dataEntries)
    {

      foreach (var dataEntry in dataEntries)
      {
        var dataItem = dataEntry.DataItem;
        var elementIndex = dataEntry.ElementIndex;

        float[] data = dataItem.CreateTimeSeriesData(elementIndex);
        int length = data.Length;

        Marshal.Copy(data, 0, intPointer, length);

        int size = sizeof(float);
        intPointer = IntPtr.Add(intPointer, length * size);
      }
    }
  }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using DHI.Generic.MikeZero.DFS;
using DHI.Mike1D.Generic;
using DHI.Mike1D.ResultDataAccess;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// Class for merging MIKE 1D res1d result files.
  /// </summary>
  public class ResultMerger
  {
    /// <summary>
    /// Instances of ResultData which will be merged.
    /// </summary>
    protected IList<ResultData> _resultDataCollection;

    /// <summary>
    /// Result data, where the merged results will be stored.
    /// </summary>
    protected ResultData _resultData;

    /// <inheritdoc cref="LTSResultMerger" />
    public ResultMerger(IList<ResultData> resultDataCollection)
    {
      _resultDataCollection = resultDataCollection;
      _resultData = _resultDataCollection.First();
    }

    /// <summary>
    /// Create particular ResultMerger class depending on the result type.
    /// </summary>
    public static ResultMerger Create(IList<ResultData> resultDataCollection)
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
          return new ResultMerger(resultDataCollection);
      }
    }

    #region Static Merge methods

    /// <summary>
    /// Merge result files given by their file names
    /// </summary>
    public static ResultData Merge(IList<string> resultFileNames, string mergedFileName = null)
    {
      var resultFilePaths = resultFileNames.Select(name => new FilePath(name)).ToList();
      return Merge(resultFilePaths, mergedFileName);
    }

    /// <summary>
    /// Merge result files given by their FilePath specification.
    /// </summary>
    public static ResultData Merge(IList<FilePath> resultFilePaths, string mergedFileName = null)
    {
      var resultData = resultFilePaths.Select(path => LoadFileHeader(path.FullFilePath)).ToList();
      return Merge(resultData, mergedFileName);
    }

    /// <summary>
    /// Merge result files given by their ResultData specification.
    /// </summary>
    public static ResultData Merge(IList<ResultData> resultDataCollection, string mergedFileName = null)
    {
      var merger = Create(resultDataCollection);
      return merger.Merge(mergedFileName);
    }

    /// <summary>
    /// Loads a file based on the filename.
    /// </summary>
    private static ResultData LoadFileHeader(string fileName)
    {
      var res = new ResultData();
      res.Connection = Connection.Create(fileName);

      var diagnostics = new Diagnostics("Result merging");
      res.LoadHeader(diagnostics);

      return res;
    }

    #endregion Static Merge methods

    /// <summary>
    /// Performs the actual merging of result files.
    /// </summary>
    /// <param name="mergedFileName">File name to save to.</param>
    /// <returns>ResultData corresponding to a merged file.</returns>
    public virtual ResultData Merge(string mergedFileName = null)
    {
      if (string.IsNullOrEmpty(mergedFileName))
        throw new ArgumentException("To merge regular res1d files destination file name needs to be specified.");

      CopyFileIfNeeded(mergedFileName);

      foreach (var sourceResultData in _resultDataCollection)
      {
        if (sourceResultData.Equals(_resultData))
          continue;

        AppendToFile(mergedFileName, sourceResultData.Connection.FilePath.FullFilePath);
      }

      var resultData = LoadFileHeader(mergedFileName);
      return resultData;
    }

    private void CopyFileIfNeeded(string mergedFileName)
    {
      var mergedFilePath = new FilePath(mergedFileName);
      string firstFullPath = _resultData.Connection.FilePath.FullFilePath;
      string mergedFullPath = mergedFilePath.FullFilePath;
      if (firstFullPath.Equals(mergedFullPath))
        return;

      CreateDirectory(mergedFullPath);
      File.Copy(firstFullPath, mergedFileName, true);
    }

    private void CreateDirectory(string fileName)
    {
      string directory = Path.GetDirectoryName(fileName);
      if (!string.IsNullOrWhiteSpace(directory))
        Directory.CreateDirectory(directory);
    }

    /// <summary>
    /// Appends data from one file to another. It is assumed that:
    /// <list type="bullet">
    /// <item>The files has identical dynamic and static items</item>
    /// <item>The last time step of the target file is equal to the first
    ///       time step of the source file, and therefor the first time step
    ///       from the source file is not added to the target file</item>
    /// </list>
    /// <para>
    /// This example uses the generic DFS functionality, and will work for any type
    /// of DFS file.
    /// </para>
    /// <para>
    /// Taken from https://github.com/DHI/MIKECore-Examples/blob/master/Examples/CSharp/ExamplesMisc.cs
    /// ExamplesMisc.AppendToFile
    /// </para>
    /// </summary>
    private void AppendToFile(string targetFile, string sourceFile)
    {
      // Open target for appending and source for reading
      var target = DfsFileFactory.DfsGenericOpenAppend(targetFile);
      var source = DfsFileFactory.DfsGenericOpen(sourceFile);

      // Time of last time step of file, in the time unit of the time axis.
      // This is sufficient as long as TimeAxis.StartTimeOffset equals in 
      // source and target file (it is zero for most files)
      var targetEndTime = target.FileInfo.TimeAxis.TimeSpan();

      // Do not add initial time step 0 of source to target file, 
      // so go directly to time step 1 in source
      source.FindTimeStep(1);

      // Copy over data
      IDfsItemData sourceData2;
      while (null != (sourceData2 = source.ReadItemTimeStepNext()))
        target.WriteItemTimeStepNext(targetEndTime + sourceData2.Time, sourceData2.Data);

      // Close the files
      target.Close();
      source.Close();
    }
  }
}

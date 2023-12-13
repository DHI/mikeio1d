using System.Collections.Generic;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// List of LTS events stored in result files.
  /// </summary>
  public class LTSResultEvents : List<LTSResultEvent>
  {
    /// <summary>
    /// Sort the event list on the first value of each event
    /// </summary>
    public void SortOnValue()
    {
      Sort(CompareValue);
    }

    /// <summary>
    /// Sort on first value, and if the same, then on time.
    /// </summary>
    public int CompareValue(LTSResultEvent e1, LTSResultEvent e2)
    {
      int cvalue = e2.Value.CompareTo(e1.Value);
      if (cvalue == 0)
        cvalue = e1.Time.CompareTo(e2.Time);
      return cvalue;
    }
  }

  /// <summary>
  /// LTS event.
  /// </summary>
  public class LTSResultEvent
  {
    /// <summary>
    /// Value of the LTS event.
    /// </summary>
    public double Value;

    /// <summary>
    /// Time of the LTS event.
    /// </summary>
    public double Time;
  }
}

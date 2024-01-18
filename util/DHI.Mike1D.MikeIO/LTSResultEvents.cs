using System;
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

    /// <summary>
    /// Sort the event list on time stamps.
    /// </summary>
    public void SortOnTimePeriod()
    {
      Sort((e1, e2) => ((LTSResultEventPeriodic)e1).TimePeriod.CompareTo(((LTSResultEventPeriodic)e2).TimePeriod));
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

  /// <summary>
  /// An LTS periodic event.
  /// </summary>
  public class LTSResultEventPeriodic : LTSResultEvent
  {
    /// <summary>
    /// Number of events (Count) in a period.
    /// </summary>
    public int Count;

    /// <summary>
    /// Duration of events in a period.
    /// </summary>
    public double Duration;

    /// <summary>
    /// Time period (year or month) represented as DateTime.
    /// </summary>
    public DateTime TimePeriod;
  }
}

using System;
using System.Collections.Generic;

namespace DHI.Mike1D.MikeIO
{
  /// <summary>
  /// List of LTS events stored in result files.
  /// </summary>
  public class LTSResultEvents : List<LTSResultEvent>
  {
  }

  /// <summary>
  /// LTS event.
  /// </summary>
  public class LTSResultEvent : IComparable<LTSResultEvent>
  {
    /// <summary>
    /// Value of the LTS event.
    /// </summary>
    public double Value;

    /// <summary>
    /// Time of the LTS event.
    /// </summary>
    public double Time;

    /// <inheritdoc />
    public virtual int CompareTo(LTSResultEvent other)
    {
      int cvalue = other.Value.CompareTo(Value);
      if (cvalue == 0)
        cvalue = Time.CompareTo(other.Time);
      return cvalue;
    }
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

    /// <inheritdoc />
    public override int CompareTo(LTSResultEvent other)
    {
      var otherPeriodic = (LTSResultEventPeriodic) other;
      return TimePeriod.CompareTo(otherPeriodic.TimePeriod);
    }
  }
}

# Manually-Created Data

This folder is used to hold manually created data that cannot be easily replicated.
You may keep data here and keep it under version control if it is small enough.
Keeping this data under version control can provide some peace of mind
that the data is not inadvertently modified.
Also, keep in mind that Git LFS is a good option if the data is large.

## `fomc_meetings.csv`

Scheduled FOMC meeting dates, transcribed from the Federal Reserve's calendar:
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

Columns:

- `meeting_start`: first day of the (usually two-day) meeting
- `meeting_end`: final day of the meeting — the policy decision is announced
  at about 2:00 p.m. ET on this day, and any rate change takes effect the
  following business day.

**This file must be updated once a year** when the Fed announces the next
year's tentative meeting schedule. The pipeline raises an error if it cannot
find a meeting on or after the current date. Only regularly scheduled
meetings are listed; unscheduled (emergency) meetings are out of scope.
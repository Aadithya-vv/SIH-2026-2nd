
STALE_DAYS = 7


def report(rows, observations, frequency_days, as_of):
    issues = [issue for row in rows for issue in row['issues']]
    valid_times = sorted(set(o.timestamp for o in observations))
    missing_periods = sum(max(0, (b-a).days//frequency_days-1) for a,b in zip(valid_times,valid_times[1:]))
    accepted = sum(row['accepted'] for row in rows)
    latest = max(valid_times) if valid_times else None
    age = (as_of-latest).total_seconds()/86400 if latest else None
    stale = age is not None and age > max(STALE_DAYS, frequency_days*2)
    warnings = sorted(set(issues))
    if missing_periods:
        warnings.append('LARGE_TIME_GAPS')
    if stale:
        warnings.append('STALE_DATA')
    return {'rows_received':len(rows),'rows_accepted':accepted,'rows_rejected':len(rows)-accepted,
        'missing_values':issues.count('MISSING_VALUE'),'duplicates':issues.count('DUPLICATE'),
        'invalid_timestamps':issues.count('INVALID_TIMESTAMP'),'non_numeric':issues.count('NON_NUMERIC'),
        'negative_values':issues.count('NEGATIVE_VALUE'),'out_of_order':issues.count('OUT_OF_ORDER'),
        'unit_inconsistency':issues.count('UNIT_INCONSISTENCY'), 'missing_periods':missing_periods,
        'completeness_percent': round(100*(len(rows)-issues.count('MISSING_VALUE'))/len(rows),2) if rows else 0,
        'start':valid_times[0].isoformat() if valid_times else None,'end':latest.isoformat() if latest else None,
        'latest_age_days':round(age,2) if age is not None else None,'stale':stale,'warnings':warnings,
        'status':'UNUSABLE' if not accepted else ('USABLE_WITH_WARNINGS' if warnings else 'USABLE'),
        'rules':{'stale_after_days':max(STALE_DAYS,frequency_days*2),
                 'missing_periods':'floor(elapsed whole days / frequency_days) - 1 between unique timestamps',
                 'completeness':'rows with non-empty mapped date AND value / all rows',
                 'duplicates':'same timestamp and available_at within this immutable dataset; retained and flagged'}}

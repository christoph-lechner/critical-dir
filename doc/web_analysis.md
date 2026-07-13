2026-07-13

CREATE TABLE api_perf_log(
	ts TIMESTAMP WITH TIME ZONE,
	time INT,
	status INT,
	response_size INT,
	method TEXT,
	path TEXT,
	protocol TEXT
);


-- https://www.caktusgroup.com/blog/2025/06/16/avoiding-timezone-traps-correctly-extracting-datetime-subfields-django-postgresql/
-- Consider using "SET TIME ZONE 'Europe/Berlin';" at start up time of dashboard app.

We want 15-minute intervals, so lets use `DATE_BIN` instead of `DATE_TRUNC`:
```
SELECT
	DATE_BIN('15 MINUTES', ts AT TIME ZONE 'Europe/Berlin', '2026-01-01 UTC') AS h,
	COUNT(*) AS c,
	PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time) AS p50,
	PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY time) AS p90
FROM api_perf_log
WHERE
	method='GET' AND path='/myapp/api/clusters'
GROUP BY 1
ORDER BY 1;
```

Next, let's fill the gaps in the time series and report percentiles only if there is sufficient data:
```
WITH q_agg AS(
	SELECT
		DATE_BIN('15 MINUTES', ts AT TIME ZONE 'Europe/Berlin', '2026-01-01 UTC') AS h,
		COUNT(*) AS c,
		PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time) AS p50,
		PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY time) AS p90
	FROM api_perf_log
	WHERE
		method='GET' AND path='/myapp/api/clusters'
	GROUP BY 1
	ORDER BY 1
),
tser AS(
	SELECT
		generate_series(
			(SELECT MIN(h) FROM q_agg),
			(SELECT MAX(h) FROM q_agg),
			INTERVAL '15 MINUTES'
		) AS x
)
SELECT
	tser.x,
	-- if there is NO data, we report count=0 (instead of NULL)
	COALESCE(q_agg.c,0) AS c,
	-- report percentiles only when there is sufficient data
	CASE WHEN q_agg.c>=10 THEN q_agg.p50 ELSE NULL END AS p50,
	CASE WHEN q_agg.c>=10 THEN q_agg.p90 ELSE NULL END AS p90
FROM tser
LEFT JOIN q_agg ON tser.x=q_agg.h
ORDER BY tser.x;
```

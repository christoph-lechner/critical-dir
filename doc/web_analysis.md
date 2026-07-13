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

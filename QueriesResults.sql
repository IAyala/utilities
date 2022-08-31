-- Tasks table
SELECT * FROM tasks;
SELECT * FROM v_last_task_version_ids;

-- Competitors
SELECT competitorid CompNb, competitorname CompName, affiliation Country FROM competitors ORDER BY competitorid;

--All Results for a Competitor (last task versions)
SELECT c.competitorid CompID, c.competitorname CompName, c.affiliation Country, t.TaskNumber, t.TaskCode, t.Status,r.PERFORMANCE 'Result',r.PERFORMANCEPENALTY ResultPen,r."RESULT" NetResult,r.TASKPENALTY taskPen,r.COMPETITIONPENALTY CompPen,r.SCORE Score,r.NOTES Notes FROM results r INNER JOIN competitors c on c.competitorid = r.COMPETITOR_ID INNER JOIN v_last_task_version_ids t on t.TaskID = r.TASK_ID
WHERE 
	c.competitorid = 8
	--c.competitorname like '%Dominic%'
ORDER BY TaskNumber;

--All Results for a Task
SELECT c.competitorid CompID,c.competitorname CompName,c.affiliation Country,t.TaskNumber,t.TaskCode,t.Status,r.PERFORMANCE 'Result',r.PERFORMANCEPENALTY ResultPen,r."RESULT" NetResult,r.TASKPENALTY taskPen,r.COMPETITIONPENALTY CompPen,r.SCORE Score,r.NOTES Notes FROM results r INNER JOIN competitors c on c.competitorid = r.COMPETITOR_ID INNER JOIN v_last_task_version_ids t on t.TaskID = r.TASK_ID
WHERE
	t.TaskNumber = 5
ORDER BY r.SCORE desc;

select
	theTable.*
from
	(
	select
		c.competitorid CompID,
		c.competitorname Competitor,
		c.affiliation Country,
		sum(score) TotalScore,
		sum(r.COMPETITIONPENALTY) + sum(r.TASKPENALTY) TotalPenalties,
		sum(score) + sum(r.COMPETITIONPENALTY) + sum(r.TASKPENALTY) TotalIfNoPenalties
	from
		results r
	INNER JOIN competitors c on
		c.competitorid = r.COMPETITOR_ID
	INNER JOIN v_last_task_version_ids t on
		t.TaskID = r.TASK_ID
	group by
		COMPETITOR_ID
	order by
		TotalScore desc) theTable;
		--TotalIfNoPenalties desc) theTable;

-- General for last task versions with Penalties and Number of Notes
--select * from v_vtotalScores;

--select count(*)+1 from v_totalScores t1 join v_totalScores t2 on t1.TotalScore < t2.TotalScore;
	
-- Sum results (mixing task versions)
select sum(Total) TotalATope, Competitor, Country FROM (
select * from (
select sum(score) Total, c.competitorname Competitor, c.affiliation Country from results r 
INNER JOIN competitors c on c.competitorid = r.COMPETITOR_ID
INNER JOIN
	(
		select * from tasks where status = 'Final'
	) t
on r.TASK_ID = t.id
where t.nb <> 8
group by COMPETITOR_ID) left_table
UNION ALL
select * from(
select sum(score) Total, c.competitorname Competitor, c.affiliation Country from results r
INNER JOIN competitors c on c.competitorid = r.COMPETITOR_ID
INNER JOIN
	(
		select * from tasks where status = 'Official 2'
	) t
on r.TASK_ID = t.id
where t.nb = 8
group by COMPETITOR_ID) right_table
)
group by Competitor order by TotalATope desc;


SELECT
	c.competitorid CompID,
	c.competitorname CompName,
	c.affiliation Country,
	t.TaskNumber,
	t.TaskCode,
	t.Status,
	r.PERFORMANCE 'Result',
	r.PERFORMANCEPENALTY ResultPen,
	r."RESULT" NetResult,
	r.TASKPENALTY taskPen,
	r.COMPETITIONPENALTY CompPen,
	r.SCORE Score,
	r.NOTES Notes
FROM
	results r
INNER JOIN competitors c on
	c.competitorid = r.COMPETITOR_ID
INNER JOIN v_last_task_version_ids t on
	t.TaskID = r.TASK_ID
WHERE
	r.TASKPENALTY != 0 or r.COMPETITIONPENALTY != 0
ORDER BY
	TaskNumber;
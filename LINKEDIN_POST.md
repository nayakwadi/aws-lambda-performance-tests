# LinkedIn Post

---

How do you actually measure AWS Lambda performance?

Most people guess. They pick 128 MB because it's cheapest, ship it, and move on.

So I built a small lab to stop guessing.

It's a Products CRUD API: API Gateway → Lambda → DynamoDB. Nothing exotic. But I deployed the same function three times at 128 MB, 512 MB, and 1024 MB, each behind its own endpoint, so I could hit all three back to back and watch the numbers.

Here's the part people miss:

On Lambda, CPU scales with memory. So a 1024 MB function isn't just "more RAM" — it gets a bigger slice of CPU too. Which means a function can finish *faster* AND cost *less* at higher memory, because you pay per millisecond and it runs for fewer of them.

The 128 MB → 512 MB jump was big. 512 → 1024 was barely worth it. That elbow is the whole game — it's where cost and speed balance out.

How I measured it:
↳ Postman to compare per-request latency across the three tiers
↳ Postman Collection Runner for sustained traffic (100 iterations)
↳ A parallel curl script for real concurrency and cold starts
↳ CloudWatch REPORT logs for the source of truth: Duration, Init Duration, Max Memory Used

That last one matters. Your client-side timer includes the network. CloudWatch tells you what Lambda actually did — including how much memory you wasted paying for.

The whole thing is Infrastructure as Code (AWS CDK in Python), so it deploys in four commands and tears down in one. No stray resources, no surprise bill.

The lesson I keep relearning: measure, don't assume. "More memory = more money" is wrong often enough that it's worth checking every time.

So — how do you measure Lambda performance? Memory sweep? Power Tuning? Gut feel and hope? I'd like to hear what's worked for you.

#AWS #Serverless #Lambda #CloudComputing #PerformanceEngineering #DevOps

---

## Posting tips

- Attach `docs/images/architecture.png` as the post image — diagrams stop the scroll.
- The first two lines are the hook (LinkedIn truncates after ~2 lines before "see more"). They're written to make people click.
- Drop your GitHub repo link in the FIRST comment, not the post body — LinkedIn suppresses reach on posts with external links. Pin that comment.
- Best engagement windows are usually Tue–Thu mornings.
- If you ran the lab for real, replace the qualitative "big jump / barely worth it" lines with your actual ms numbers — concrete figures get far more comments than generalities.

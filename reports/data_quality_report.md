# Data Quality — events (10,564 rows)

| expectation                   | column   | critical   | result   |   unexpected_pct |
|:------------------------------|:---------|:-----------|:---------|-----------------:|
| ExpectColumnValuesToNotBeNull | id       | yes        | PASS     |            0     |
| ExpectColumnValuesToBeUnique  | id       | yes        | PASS     |            0     |
| ExpectColumnValuesToBeBetween | mag      | yes        | PASS     |            0     |
| ExpectColumnValuesToBeBetween | depth    | yes        | PASS     |            0     |
| ExpectColumnValuesToBeBetween | lat      | yes        | PASS     |            0     |
| ExpectColumnValuesToBeBetween | lon      | yes        | PASS     |            0     |
| ExpectColumnValuesToBeBetween | rms      | no         | PASS     |            0     |
| ExpectColumnValuesToBeBetween | gap      | no         | PASS     |            0     |
| ExpectColumnValuesToBeInSet   | type     | no         | PASS     |            0.009 |
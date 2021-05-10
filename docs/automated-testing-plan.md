# imProving Agent testing plan

The imProving Agent will be tested to ensure compatibility, availability
and reliability with its own components and other components in the
Translator network.

imProving Agent is developed and run in Docker, and most tests will run
in an identical environment.

## Unit tests
The imProving Agent codebase will be thoroughly tested with unit tests
to quickly identify when functions are not completing their tasks as
expected. These unit tests will evaluate all paths within a function to
confirm that all actions are proceeding as intended. The tests will
heavily utilize mocks to isolate the testing to the function in
question. Asserting for equality, for expected function arguments, and
checks for errors will be the main modality of these tests. Pytest will
be the framework used.

These tests will be run locally by developers, upon push to PRs against
the main branch, as part of image build as part of automated deployment
following merge to main. Any test failure will prevent service
deployment and the developer will be notified via email.

## Integration with other Translator components
As an ARA, imProving Agent is expected to communicate with a number of
other services as a client as part of normal operation. A suite of tests
will be written to query all configured services with simple queries to
ensure that all services are behaving as expected by the imProving
Agent. For example, these tests will query COHD or ICEES for known
co-occurrence of simple terms in a specific, static cohort. In this
example, the response will be evaluated against the expected value of
the correlation as determined manually during development. Unexpected
values or response codes will cause a test failure.

These tests will be run upon push to PRs against the main branch and
upon service build after merge to main. Failures will prevent the
service from deploying and the developer will be notified via email.

## Availability in Production
A suite of tests will be written to test imProving Agent in production
to ensure that the service is available and returning the expected
results for simple queries. These tests will be run automatically from
AWS Lambda at a high frequency. 

First, an additional endpoint will be exposed that will return "OK" and
a 200 HTTP status code to confirm that the API code is up and accepting
requests.

Second, a small set of test queries testing connection to SPOKE will
fire and compare the results to a known set of expected responses. For
example, we would expect "hypertension" as one of _n_ responses to the
query 'Aspirin treats disease.' Similar one-hop queries will be fired
and evaluated to ensure that the service is behaving as expected.
Service responses will be run through the relevant version of the TRAPI
validator.

When either of these fail, the responsible developer will be notified
via Amazon SNS.
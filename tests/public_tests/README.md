# Public-repo tests

These tests run only while our own repo, `MuhammadSban/DocumentationDrifter`, is **public**, as it has been since 2026-10-17. They check that the service analyses it anonymously through GitHub: the merge of PR #2 (`76eb691`) gives the expected `changes[]`, no credential helper is asked for anything, and `GET` returns the saved run unchanged.

While the repo is private they skip, and [`tests/private_tests`](../private_tests/README.md) runs instead. Each test asks GitHub's API, without credentials, which case applies.

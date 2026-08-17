# Third-party notices

## operator-shared-core compatibility layer

`apps/api/src/internal/vendor_core/` contains the import closure used by this
repository from `operator-shared-core` v1.3.0 at commit
`dbf276a7708da65b55e1f10b35af634b300d1f07`.

Vendored modules: `config`, `database`, `docparse`, `embeddings`, `errors`,
`evaljudge`, `health`, `llm`, `logging`, `pricing`, `redis`, `tasks`, `testing`,
and `vectorstore`.

Local namespace-only patches:

- internal imports use `apps.api.src.internal.vendor_core` instead of the
  archived top-level package;
- the optional embedding gateway uses a lazily imported HTTP client;
- Redis and Celery integrations load lazily, with a synchronous broker-free task
  registry for offline imports and tests;
- the database facade falls back to an internal SQLite engine when the optional
  PostgreSQL driver is absent.

The vendored source is licensed under the MIT License:

> Copyright (c) 2026 Operator Systems
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

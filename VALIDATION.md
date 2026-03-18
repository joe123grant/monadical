# Validation Monad Guide

`Validation[T, E]` is a data type that represents the outcome of validation. It is either `Valid(value)` — a successful result — or `Invalid(errors)` — a list of accumulated failures.

Its defining feature is **error accumulation**: unlike `Result`, which stops at the first failure, `Validation` continues checking every rule and collects every error. Use it when you want to present all problems to the user at once.

```python
from monadical.validation import (
    Validation, Valid, Invalid, Validator, Rule,
    Sequence, Traverse, Partition, Valids, Choose,
    ParseInt, ParseFloat, ParseDecimal, ParseBool,
    ParseDate, ParseDatetime, ParseTime, ParseUuid, ParseEnum, ParseRegex,
    ValidateEnv, ValidateEnvInt, ValidateEnvFloat, ValidateEnvBool,
    ValidateFile, ValidateDirectory, ValidateVisibleFile,
    ReadText, ReadBytes, ReadLines, ReadJson, ParseJson,
)
```

---

## When to use Validation vs Result vs Option

| | `Option[T]` | `Result[T]` | `Validation[T, E]` |
|---|---|---|---|
| **Success state** | `Some(value)` | `Ok(value)` | `Valid(value)` |
| **Failure state** | `Empty()` | `Failure(error)` | `Invalid(errors)` |
| **Error info** | None | One exception | List of `E` |
| **On failure** | Silently empty | Short-circuits | Keeps accumulating |
| **Use when** | Value may be absent | One thing can go wrong | Many rules must all pass |

**Concrete rule of thumb:**
- Parsing a single value that may not exist → `Option`
- A network call or file read that can fail with one error → `Result`
- Validating a form, request body, or config where you want all errors at once → `Validation`

---

## Core concepts

### The two states

```python
# Valid — wraps a successfully validated value
v = Valid(42)
v.value   # 42

# Invalid — wraps a list of one or more errors
e = Invalid(["Name is required", "Email is invalid"])
e.errors  # ["Name is required", "Email is invalid"]
```

The type parameter `E` is the error type. It is completely generic — use `str` for simple messages, a dataclass for structured errors, an enum for error codes, or anything else.

```python
from dataclasses import dataclass

@dataclass
class ValidationError:
    field: str
    message: str

Validation[str, ValidationError]   # typed error objects
Validation[int, str]               # plain string messages
Validation[User, dict]             # dict-based errors
```

### Checking the state

```python
v = Validation.Success(10)
e = Validation.Fail(["something went wrong"])

v.IsOk()       # True
v.HasErrors()  # False
e.IsOk()       # False
e.HasErrors()  # True

bool(v)  # True
bool(e)  # False
```

### Pattern matching

```python
result = validate_something(data)

match result:
    case Valid(value=v):
        print(f"Success: {v}")
    case Invalid(errors=errs):
        for err in errs:
            print(f"Error: {err}")
```

### Iteration

`Validation` supports iteration — zero items if invalid, one item if valid. Useful for comprehensions.

```python
validated = Validation.Success("hello")
list(validated)   # ["hello"]

failed = Validation.Fail(["oops"])
list(failed)      # []

# Collect all valid values from a list using a comprehension
results = [validate(x) for x in items]
values = [v for r in results for v in r]
```

---

## Constructors

### `Validation.Success(value)`

Wraps a known-good value. Use this at the end of a pipeline or when constructing a result programmatically.

```python
Validation.Success(42)          # Valid(42)
Validation.Success("hello")     # Valid('hello')
Validation.Success([1, 2, 3])   # Valid([1, 2, 3])
```

### `Validation.Fail(errors)`

Creates a failed validation. The argument must always be a **list** — even for a single error.

```python
Validation.Fail(["Name is required"])
Validation.Fail(["Too short", "No special characters"])
Validation.Fail([ValidationError(field="email", message="Invalid format")])
```

### `Validation.Require(value, error)`

Converts a nullable value to a `Validation`. Fails with a single-item error list if the value is `None`.

```python
row = {"name": "Alice", "age": None}

Validation.Require(row.get("name"), "name is required")   # Valid('Alice')
Validation.Require(row.get("age"),  "age is required")    # Invalid(['age is required'])
Validation.Require(row.get("email"), "email is required") # Invalid(['email is required'])
```

### `Validation.Try(action, on_error)`

Runs a callable and catches any exception, mapping it to a list of errors. Use at integration boundaries — third-party libraries, serialisation, type coercion.

```python
Validation.Try(
    lambda: int("42"),
    on_error=lambda e: [f"Not a number: {e}"],
)
# Valid(42)

Validation.Try(
    lambda: int("abc"),
    on_error=lambda e: [f"Not a number: {e}"],
)
# Invalid(["Not a number: invalid literal for int() with base 10: 'abc'"])
```

`on_error` receives the raw `Exception` and must return `list[E]`.

```python
# Structured errors
Validation.Try(
    lambda: json.loads(raw),
    on_error=lambda e: [ValidationError(field="body", message=str(e))],
)

# Multiple errors from one exception (unusual, but valid)
Validation.Try(
    lambda: parse_csv_row(row),
    on_error=lambda e: [f"CSV parse error at column {i}: {e}" for i in bad_columns],
)
```

---

## Building pipelines — `Validation.Where`, `Rule`, and `Validator`

This is the primary way to build reusable, composable validators.

### `Rule(predicate, error)`

Creates a validator function from a boolean predicate and a single error value. The returned function takes a value and returns `Valid(value)` if the predicate passes, or `Invalid([error])` if it fails.

```python
from monadical.validation import Rule

not_empty   = Rule(lambda s: len(s) > 0,    "Cannot be empty")
min_2_chars = Rule(lambda s: len(s) >= 2,   "Must be at least 2 characters")
max_50_chars = Rule(lambda s: len(s) <= 50, "Cannot exceed 50 characters")
letters_only = Rule(lambda s: s.isalpha(),  "Must contain only letters")
positive     = Rule(lambda n: n > 0,        "Must be positive")
non_negative = Rule(lambda n: n >= 0,       "Must be non-negative")
is_adult     = Rule(lambda n: n >= 18,      "Must be 18 or older")
```

`Rule` is also available as a static method on `Validation`:

```python
Validation.Rule(lambda s: len(s) > 0, "Cannot be empty")
# identical to Rule(lambda s: len(s) > 0, "Cannot be empty")
```

### `Validation.Where(rule)` → `Validator`

Starts a composable pipeline. Takes any callable `T -> Validation[T, E]` and returns a `Validator` you can extend with `.And` and `.Then`.

```python
validator = Validation.Where(not_empty)
result = validator("hello")  # Valid('hello')
result = validator("")       # Invalid(['Cannot be empty'])
```

### `Validator.And(rule)` — parallel, accumulating

Adds a rule that runs **on the same input** as all previous rules. Both rules run regardless of whether the other passes. All errors are collected.

```python
validate_name = (
    Validation.Where(Rule(lambda s: len(s) >= 2, "Too short"))
              .And(Rule(lambda s: len(s) <= 50,  "Too long"))
              .And(Rule(lambda s: s.isalpha(),   "Letters only"))
)

validate_name("Alice")    # Valid('Alice')
validate_name("A")        # Invalid(['Too short', 'Letters only']) — both collected
validate_name("Al")       # Valid('Al')
validate_name("Al9!")     # Invalid(['Letters only'])
validate_name("")         # Invalid(['Too short', 'Letters only'])
```

The rule: if a value fails two `.And` checks, you get two errors. If it fails one, you get one.

### `Validator.Then(transform)` — sequential, short-circuit

Adds a step that receives the **output of the previous step** as its input. If any earlier step failed, this step is skipped entirely. Use `.Then` to chain dependent operations — for example, parse a raw string first, then validate the parsed value.

```python
parse_and_validate_age = (
    Validation.Where(ParseInt)                              # str → int
              .Then(Rule(lambda n: n >= 0,   "Must be non-negative"))
              .Then(Rule(lambda n: n <= 120, "Unrealistic age"))
)

parse_and_validate_age("25")    # Valid(25)
parse_and_validate_age("-1")    # Invalid(['Must be non-negative'])
parse_and_validate_age("999")   # Invalid(['Unrealistic age'])
parse_and_validate_age("abc")   # Invalid(['ParseInt: cannot parse 'abc': ...'])
                                # — stops at ParseInt, downstream rules never run
```

### Mixing `.And` and `.Then`

```python
validate_username = (
    Validation.Where(ParseInt)          # parse step — sequential
              .Then(                    # from here on, working with an int
                  Validation.Where(Rule(lambda n: n > 0,     "Must be positive"))
                             .And(Rule(lambda n: n < 1_000_000, "Too large"))
              )
)

# Or using a helper function as a .Then target:
def validate_email_domain(email: str) -> Validation[str, str]:
    allowed = {"example.com", "company.org"}
    domain = email.split("@")[-1]
    return (
        Validation.Success(email)
        if domain in allowed
        else Validation.Fail([f"Domain '{domain}' is not allowed"])
    )

validate_email = (
    Validation.Where(Rule(lambda s: "@" in s, "Must contain @"))
              .And(Rule(lambda s: len(s) <= 254, "Too long"))
              .Then(validate_email_domain)    # only runs if both .And checks pass
)
```

### Validators are callables

A `Validator` is just a callable. Pass it anywhere a function is expected.

```python
validate_age = Validation.Where(ParseInt).Then(Rule(lambda n: n >= 0, "Must be non-negative"))

# Call directly
validate_age("25")   # Valid(25)

# Pass to combinators
ages = ["25", "bad", "30", "-1"]
Traverse(ages, validate_age)
# Invalid(['ParseInt: cannot parse 'bad'...', 'Must be non-negative'])
```

---

## Instance methods on `Validation`

### `Match(on_ok, on_error)` — exhaustive handler

The fundamental operation. Handles both states and produces a single output. Both branches must return the same type.

```python
v = Validation.Success(42)
e = Validation.Fail(["something broke"])

v.Match(
    on_ok=lambda n: f"Result: {n}",
    on_error=lambda errs: f"Errors: {', '.join(errs)}",
)
# "Result: 42"

e.Match(
    on_ok=lambda n: f"Result: {n}",
    on_error=lambda errs: f"Errors: {', '.join(errs)}",
)
# "Errors: something broke"
```

Using `Match` to build a response:

```python
def to_http_response(v: Validation[User, str]) -> dict:
    return v.Match(
        on_ok=lambda user: {"status": 200, "data": user.to_dict()},
        on_error=lambda errs: {"status": 422, "errors": errs},
    )
```

### `Map(func)` — transform the valid value

Applies a pure function to the value if valid. Errors pass through unchanged. The function returns a plain value, not a `Validation`.

```python
Validation.Success("  hello  ").Map(str.strip)        # Valid('hello')
Validation.Success("hello").Map(str.upper)             # Valid('HELLO')
Validation.Success(42).Map(lambda n: n * 2)            # Valid(84)
Validation.Fail(["oops"]).Map(lambda n: n * 2)         # Invalid(['oops'])

# Chaining maps
Validation.Success("  Hello World  ") \
    .Map(str.strip) \
    .Map(str.lower) \
    .Map(lambda s: s.replace(" ", "_"))
# Valid('hello_world')
```

### `Then(func)` — chain a validation-returning function (sequential)

Like `Map`, but `func` returns a `Validation`. Short-circuits on failure.

```python
def validate_positive(n: int) -> Validation[int, str]:
    return Validation.Success(n) if n > 0 else Validation.Fail(["Must be positive"])

ParseInt("10").Then(validate_positive)   # Valid(10)
ParseInt("-5").Then(validate_positive)   # Invalid(['Must be positive'])
ParseInt("abc").Then(validate_positive)  # Invalid(['ParseInt: ...']) — validate_positive never called
```

`Then` is the sequential building block for multi-step pipelines:

```python
def load_user(user_id: int) -> Validation[User, str]:
    user = db.find(user_id)
    return Validation.Require(user, f"No user with id {user_id}")

def ensure_active(user: User) -> Validation[User, str]:
    return (
        Validation.Success(user)
        if user.is_active
        else Validation.Fail([f"User {user.id} is inactive"])
    )

def ensure_admin(user: User) -> Validation[User, str]:
    return (
        Validation.Success(user)
        if user.role == "admin"
        else Validation.Fail([f"User {user.id} does not have admin privileges"])
    )

get_admin_user = (
    ParseInt                # str → int
    >> (lambda id_: load_user(id_).Then(ensure_active).Then(ensure_admin))
)
```

### `MapErrors(func)` — transform each error

Applies a function to every error in the list. Valid values pass through unchanged. Useful for converting between error representations.

```python
v = Validation.Fail(["name is required", "email is invalid"])

v.MapErrors(str.upper)
# Invalid(['NAME IS REQUIRED', 'EMAIL IS INVALID'])

v.MapErrors(lambda msg: {"message": msg, "code": "VALIDATION_ERROR"})
# Invalid([{'message': 'name is required', 'code': 'VALIDATION_ERROR'},
#          {'message': 'email is invalid',  'code': 'VALIDATION_ERROR'}])
```

### `Catch(func)` — recover from or transform failures

Chains a function on the **error side**. `func` receives the full error list and returns a new `Validation`. Valid values pass straight through.

```python
v = Validation.Fail(["name is required"])

# Recover with a default
v.Catch(lambda errs: Validation.Success("Anonymous"))
# Valid('Anonymous')

# Re-wrap with additional context
v.Catch(lambda errs: Validation.Fail([f"[signup] {e}" for e in errs]))
# Invalid(['[signup] name is required'])

# Conditional recovery
def maybe_recover(errs: list[str]) -> Validation[str, str]:
    if all("optional" in e for e in errs):
        return Validation.Success("")
    return Validation.Fail(errs)

v.Catch(maybe_recover)
```

### `Apply(other, combiner)` — combine two validations, accumulate errors

The core combinator for error accumulation. Both validations run independently; if both fail, all errors from both are collected.

```python
name_v = Validation.Success("Alice")
age_v  = Validation.Success(30)

name_v.Apply(age_v, lambda name, age: {"name": name, "age": age})
# Valid({'name': 'Alice', 'age': 30})

# When one fails
Validation.Fail(["name required"]).Apply(Validation.Success(30), lambda n, a: (n, a))
# Invalid(['name required'])

# When both fail — errors accumulate
Validation.Fail(["name required"]).Apply(Validation.Fail(["age required"]), lambda n, a: (n, a))
# Invalid(['name required', 'age required'])
```

### `&` operator — shorthand for `Apply` with tuple output

Combines two validations into a tuple, accumulating errors.

```python
name_v  = Validation.Success("Alice")
age_v   = Validation.Success(30)
email_v = Validation.Success("alice@example.com")

name_v & age_v
# Valid(('Alice', 30))

name_v & age_v & email_v
# Valid((('Alice', 30), 'alice@example.com'))

# Error accumulation
Validation.Fail(["bad name"]) & Validation.Fail(["bad email"])
# Invalid(['bad name', 'bad email'])
```

**Validating an entire object at once:**

```python
from dataclasses import dataclass

@dataclass
class SignupForm:
    name: str
    age: int
    email: str

def validate_signup(raw: dict) -> Validation[SignupForm, str]:
    name_v  = validate_name(raw.get("name"))
    age_v   = validate_age(raw.get("age"))
    email_v = validate_email(raw.get("email"))

    return (name_v & age_v & email_v).Map(
        lambda t: SignupForm(name=t[0][0], age=t[0][1], email=t[1])
    )

validate_signup({"name": "", "age": -1, "email": "notanemail"})
# Invalid(['Too short', 'Letters only', 'Must be non-negative', 'Must contain @'])
# — every problem reported at once
```

### `Tap(action)` — side effect on valid value

Executes a side effect when valid, then returns the original `Validation` unchanged. Useful for logging, metrics, or caching mid-pipeline without breaking the chain.

```python
import logging

result = (
    validate_user(payload)
    .Tap(lambda user: logging.info(f"Validated user: {user.id}"))
    .Tap(lambda user: metrics.increment("users.validated"))
    .Map(lambda user: save_to_db(user))
)
```

### `TapErrors(action)` — side effect on errors

Executes a side effect when invalid, returns unchanged. Use for logging failures.

```python
result = (
    validate_form(data)
    .TapErrors(lambda errs: logging.warning(f"Validation failed: {errs}"))
    .TapErrors(lambda errs: sentry.capture(errs))
)
```

### `Unwrap()` — extract or raise

Returns the valid value directly. Raises `ValueError` if the validation is invalid. Only use this when you are certain the validation will succeed, or when a hard failure is appropriate.

```python
v = Validation.Success(42)
v.Unwrap()   # 42

e = Validation.Fail(["something went wrong"])
e.Unwrap()   # raises ValueError: Validation failed: ['something went wrong']
```

### `GetOrElse(fallback)` — extract with computed default

Returns the valid value, or computes a fallback from the error list.

```python
Validation.Success(42).GetOrElse(lambda errs: 0)     # 42
Validation.Fail(["oops"]).GetOrElse(lambda errs: -1)  # -1

# Use the error list in the fallback
Validation.Fail(["field A missing", "field B missing"]).GetOrElse(
    lambda errs: f"Default applied due to: {'; '.join(errs)}"
)
# "Default applied due to: field A missing; field B missing"
```

### `GetOr(default)` — extract with constant default

```python
Validation.Success("alice").GetOr("anonymous")   # "alice"
Validation.Fail(["no name"]).GetOr("anonymous")  # "anonymous"
```

### `Otherwise(other)` — fallback with error accumulation

Returns `self` if valid. If invalid, tries `other`. If both are invalid, accumulates all errors from both.

```python
primary   = Validation.Fail(["primary failed"])
secondary = Validation.Success("fallback value")
tertiary  = Validation.Fail(["tertiary also failed"])

primary.Otherwise(secondary)            # Valid('fallback value')
secondary.Otherwise(primary)            # Valid('fallback value') — self is valid, used directly
primary.Otherwise(tertiary)             # Invalid(['primary failed', 'tertiary also failed'])

# Try multiple sources in order, report all failures if all miss
read_from_db.Otherwise(read_from_cache).Otherwise(read_from_disk)
```

### `Flatten()` — unwrap a nested `Validation[Validation[T, E], E]`

```python
inner = Validation.Success(42)
outer = Validation.Success(inner)

outer.Flatten()   # Valid(42)

# Practical: when a function returns Validation[Validation[T, E], E]
Validation.Success(Validation.Fail(["inner error"])).Flatten()
# Invalid(['inner error'])
```

### `Exists(predicate)` — check a predicate on the valid value

Returns `True` if valid and the predicate holds; `False` if invalid or predicate fails.

```python
Validation.Success(42).Exists(lambda n: n > 0)    # True
Validation.Success(-1).Exists(lambda n: n > 0)    # False
Validation.Fail(["err"]).Exists(lambda n: n > 0)  # False
```

### `ForAll(predicate)` — vacuously true when invalid

Returns `True` if invalid (no value to violate the predicate), or if valid and the predicate holds.

```python
Validation.Success(42).ForAll(lambda n: n > 0)    # True
Validation.Success(-1).ForAll(lambda n: n > 0)    # False
Validation.Fail(["err"]).ForAll(lambda n: n > 0)  # True — vacuously true
```

### `ToOption()` — convert to `Option`, discard errors

```python
from monadical.option import Option

Validation.Success(42).ToOption()       # Some(42)
Validation.Fail(["oops"]).ToOption()    # Empty()
```

Use this when moving from "collect all errors" to "just care about the value".

### `ToResult(error_mapper)` — convert to `Result`, collapse errors into one exception

```python
from monadical.result import Result

v = Validation.Success(42)
v.ToResult(lambda errs: ValueError("; ".join(errs)))
# Ok(42)

e = Validation.Fail(["name required", "email invalid"])
e.ToResult(lambda errs: ValueError("; ".join(errs)))
# Failure(ValueError('name required; email invalid'))
```

### Async methods

```python
async def fetch_user(user_id: int) -> User:
    return await db.get(user_id)

async def validate_user_async(user_id: int) -> Validation[User, str]:
    return await ParseInt(str(user_id)).MapAsync(fetch_user)

# MatchAsync
result = await validated.MatchAsync(
    on_ok=lambda user: send_welcome_email(user),
    on_error=lambda errs: log_errors(errs),
)

# ThenAsync
result = await ParseInt(raw_id).ThenAsync(
    lambda id_: fetch_and_validate_user(id_)
)
```

---

## Combinators

Combinators operate over collections of `Validation` values. Import from `monadical.validation`.

### `Valids(validations)` — extract all valid values

Returns a plain list of all values that passed validation, silently discarding all failures.

```python
from monadical.validation import Valids

results = [ParseInt("1"), ParseInt("bad"), ParseInt("3"), ParseInt("also_bad")]
Valids(results)   # [1, 3]

# Typical usage: parse a mixed list and take what works
raw_ids = ["1", "2", "abc", "4", ""]
Valids(ParseInt(s) for s in raw_ids)   # [1, 2, 4]
```

### `Sequence(validations)` — all-or-nothing with full error accumulation

Runs every validation in the iterable. If **all** pass, returns `Valid(list_of_values)`. If **any** fail, returns `Invalid` with **every error from every failure** — it never short-circuits.

```python
from monadical.validation import Sequence

Sequence([ParseInt("1"), ParseInt("2"), ParseInt("3")])
# Valid([1, 2, 3])

Sequence([ParseInt("1"), ParseInt("bad"), ParseInt("3"), ParseInt("also_bad")])
# Invalid(['ParseInt: cannot parse 'bad': ...', 'ParseInt: cannot parse 'also_bad': ...'])
# — errors from positions 1 and 3 both present; the valid values at 0 and 2 are discarded

Sequence([])
# Valid([])
```

This is the key difference from `Result.Sequence`, which would stop at the first failure.

**Validating a list of form fields:**

```python
fields = ["email@example.com", "not-an-email", "another@example.com", "bad"]

results = [validate_email(f) for f in fields]
Sequence(results)
# Invalid(['not-an-email is not a valid email', 'bad is not a valid email'])
# — you know every field that failed, not just the first one
```

### `Traverse(items, func)` — map then sequence, with full error accumulation

Applies `func` to each item, then behaves exactly like `Sequence` on the results. Errors from all failing items are collected.

```python
from monadical.validation import Traverse

Traverse(["1", "2", "3"], ParseInt)
# Valid([1, 2, 3])

Traverse(["1", "bad", "3", "also_bad"], ParseInt)
# Invalid(['ParseInt: cannot parse 'bad': ...', 'ParseInt: cannot parse 'also_bad': ...'])

# Validate every row in a CSV upload:
def validate_row(row: dict) -> Validation[ProcessedRow, str]:
    return (
        validate_name(row.get("name"))
        & validate_email(row.get("email"))
        & validate_age(row.get("age"))
    ).Map(lambda t: ProcessedRow(name=t[0][0], email=t[0][1], age=t[1]))

Traverse(csv_rows, validate_row)
# Either Valid([list of ProcessedRow]) or Invalid([all errors from all rows])
```

### `Partition(validations)` — separate successes from failures

Returns a tuple `(valid_values, all_errors)`. Unlike `Sequence`, this never fails — it always splits the input into what worked and what didn't. Errors from all invalid validations are flattened into one list.

```python
from monadical.validation import Partition

results = [ParseInt("1"), ParseInt("bad"), ParseInt("3"), ParseInt("also_bad")]
values, errors = Partition(results)
# values: [1, 3]
# errors: ['ParseInt: cannot parse 'bad': ...', 'ParseInt: cannot parse 'also_bad': ...']
```

Use `Partition` when you want to process whatever succeeded while also reporting what failed — for example, in a bulk import where partial success is acceptable.

```python
rows = load_csv("import.csv")
valid_rows, errors = Partition(validate_row(r) for r in rows)

if errors:
    report_import_warnings(errors)

save_all(valid_rows)   # save whatever passed
```

### `Choose(items, func)` — filter-map, discard failures silently

Applies `func` to each item and returns only the valid values. Failures are silently dropped — no error list is produced.

```python
from monadical.validation import Choose

Choose(["1", "bad", "3", "also_bad"], ParseInt)
# [1, 3]

# Filter a mixed list of strings, keeping only valid UUIDs
Choose(raw_ids, ParseUuid)

# Filter config entries, keeping only valid ports
Choose(port_strings, lambda s: ParseInt(s).Then(Rule(lambda n: 1 <= n <= 65535, "Invalid port")))
```

`Choose` is to `Traverse` as `Valids` is to `Sequence` — it trades error information for simplicity.

---

## Parse functions

All parse functions live in `monadical.validation.parse` and are re-exported from `monadical.validation`. They return `Validation[T, str]` — string error messages. They strip whitespace before parsing.

### `ParseInt(value, base=10)`

```python
ParseInt("42")         # Valid(42)
ParseInt("  42  ")     # Valid(42) — strips whitespace
ParseInt("ff", 16)     # Valid(255)
ParseInt("abc")        # Invalid(["ParseInt: cannot parse 'abc': ..."])
ParseInt(None)         # Invalid(["ParseInt: value is None"])
ParseInt("")           # Invalid(["ParseInt: value is empty"])
ParseInt("  ")         # Invalid(["ParseInt: value is empty"])
```

### `ParseFloat(value)`

Rejects `nan`, `inf`, and `-inf` as non-finite.

```python
ParseFloat("3.14")     # Valid(3.14)
ParseFloat("-0.5")     # Valid(-0.5)
ParseFloat("nan")      # Invalid(["ParseFloat: 'nan' is not finite"])
ParseFloat("inf")      # Invalid(["ParseFloat: 'inf' is not finite"])
ParseFloat("abc")      # Invalid(["ParseFloat: cannot parse 'abc': ..."])
ParseFloat(None)       # Invalid(["ParseFloat: value is None"])
```

### `ParseDecimal(value)`

Uses Python's `Decimal` for arbitrary precision. Also rejects non-finite values.

```python
from decimal import Decimal

ParseDecimal("3.14159265358979323846")   # Valid(Decimal('3.14159265358979323846'))
ParseDecimal("1.5")                      # Valid(Decimal('1.5'))
ParseDecimal("NaN")                      # Invalid(["ParseDecimal: 'NaN' is not finite"])
ParseDecimal("Infinity")                 # Invalid(["ParseDecimal: 'Infinity' is not finite"])
ParseDecimal("abc")                      # Invalid(["ParseDecimal: cannot parse 'abc': ..."])
```

### `ParseBool(value, truthy=..., falsy=...)`

Accepts any value (converts to string first). Default truthy set: `true, 1, yes, on, y`. Default falsy set: `false, 0, no, off, n`. Case-insensitive.

```python
ParseBool("true")    # Valid(True)
ParseBool("YES")     # Valid(True)
ParseBool("1")       # Valid(True)
ParseBool("on")      # Valid(True)
ParseBool("false")   # Valid(False)
ParseBool("NO")      # Valid(False)
ParseBool("0")       # Valid(False)
ParseBool(True)      # Valid(True)   — non-string input converted via str()
ParseBool(1)         # Valid(True)
ParseBool("maybe")   # Invalid(["ParseBool: cannot interpret 'maybe' as bool"])
ParseBool(None)      # Invalid(["ParseBool: value is None"])

# Custom truthy/falsy sets
ParseBool("enabled",  truthy=frozenset({"enabled"}), falsy=frozenset({"disabled"}))
ParseBool("disabled", truthy=frozenset({"enabled"}), falsy=frozenset({"disabled"}))
```

### `ParseDate(value, fmt="%Y-%m-%d")`

```python
from datetime import date

ParseDate("2024-01-15")               # Valid(date(2024, 1, 15))
ParseDate("15/01/2024", "%d/%m/%Y")   # Valid(date(2024, 1, 15))
ParseDate("not-a-date")               # Invalid(["ParseDate: cannot parse 'not-a-date' with format '%Y-%m-%d': ..."])
ParseDate("2024-13-01")               # Invalid([...]) — month 13 doesn't exist
ParseDate(None)                       # Invalid(["ParseDate: value is None"])
```

### `ParseDatetime(value, fmt="%Y-%m-%dT%H:%M:%S")`

```python
from datetime import datetime

ParseDatetime("2024-01-15T09:30:00")               # Valid(datetime(2024, 1, 15, 9, 30, 0))
ParseDatetime("15/01/2024 09:30", "%d/%m/%Y %H:%M") # Valid(datetime(2024, 1, 15, 9, 30))
ParseDatetime("not a datetime")                     # Invalid([...])
```

### `ParseTime(value, fmt="%H:%M:%S")`

```python
from datetime import time

ParseTime("09:30:00")               # Valid(time(9, 30, 0))
ParseTime("09:30", "%H:%M")         # Valid(time(9, 30, 0))
ParseTime("25:00:00")               # Invalid([...]) — hour 25 invalid
ParseTime(None)                     # Invalid(["ParseTime: value is None"])
```

### `ParseUuid(value)`

```python
from uuid import UUID

ParseUuid("550e8400-e29b-41d4-a716-446655440000")   # Valid(UUID('550e8400-...'))
ParseUuid("not-a-uuid")                             # Invalid(["ParseUuid: cannot parse 'not-a-uuid': ..."])
ParseUuid(None)                                     # Invalid(["ParseUuid: value is None"])
```

### `ParseEnum(value, enum_type, case_sensitive=False)`

Matches against enum member **names** (not values). Case-insensitive by default.

```python
from enum import Enum

class Colour(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

ParseEnum("red",   Colour)   # Valid(Colour.RED)
ParseEnum("GREEN", Colour)   # Valid(Colour.GREEN)
ParseEnum("Blue",  Colour)   # Valid(Colour.BLUE)
ParseEnum("pink",  Colour)   # Invalid(["ParseEnum: 'pink' is not a member of Colour"])
ParseEnum(None,    Colour)   # Invalid(["ParseEnum: value is None"])

# Case-sensitive matching
ParseEnum("RED",   Colour, case_sensitive=True)   # Valid(Colour.RED)
ParseEnum("red",   Colour, case_sensitive=True)   # Invalid([...])
```

### `ParseRegex(value, pattern, group=0)`

Matches a regex against the value. `group=0` returns the full match; pass an integer or named group string to extract a capture group.

```python
ParseRegex("hello world", r"\w+")           # Valid('hello') — group 0 = full match of first \w+
ParseRegex("user@example.com", r"@(\w+)")   # Valid('user@example.com') — group 0
ParseRegex("user@example.com", r"@(\w+)", group=1)  # Valid('example')

ParseRegex("123-456-7890", r"(\d{3})-(\d{3})-(\d{4})", group=1)  # Valid('123')
ParseRegex("no-match-here", r"\d{10}")   # Invalid(["ParseRegex: pattern '\\d{10}' did not match 'no-match-here'"])
ParseRegex(None, r"\w+")                 # Invalid(["ParseRegex: value is None"])
```

---

## Environment variables

All functions in `monadical.validation.env`. They fail with a clear string error if the variable is unset or blank.

### `ValidateEnv(key)`

```python
import os
os.environ["APP_NAME"] = "myapp"

ValidateEnv("APP_NAME")      # Valid('myapp')
ValidateEnv("MISSING_KEY")   # Invalid(["Environment variable 'MISSING_KEY' is not set"])

os.environ["BLANK"] = "   "
ValidateEnv("BLANK")         # Invalid(["Environment variable 'BLANK' is empty"])
```

### `ValidateEnvInt(key, base=10)`

```python
os.environ["PORT"] = "8080"
ValidateEnvInt("PORT")         # Valid(8080)
ValidateEnvInt("MISSING")      # Invalid(["Environment variable 'MISSING' is not set"])

os.environ["BAD_PORT"] = "abc"
ValidateEnvInt("BAD_PORT")     # Invalid(["ParseInt: cannot parse 'abc': ..."])

os.environ["HEX_VAL"] = "ff"
ValidateEnvInt("HEX_VAL", 16)  # Valid(255)
```

### `ValidateEnvFloat(key)`

```python
os.environ["TIMEOUT"] = "30.5"
ValidateEnvFloat("TIMEOUT")   # Valid(30.5)

os.environ["BAD"] = "inf"
ValidateEnvFloat("BAD")       # Invalid(["ParseFloat: 'inf' is not finite"])
```

### `ValidateEnvBool(key)`

```python
os.environ["DEBUG"] = "true"
ValidateEnvBool("DEBUG")    # Valid(True)

os.environ["VERBOSE"] = "0"
ValidateEnvBool("VERBOSE")  # Valid(False)

os.environ["UNKNOWN"] = "maybe"
ValidateEnvBool("UNKNOWN")  # Invalid(["ParseBool: cannot interpret 'maybe' as bool"])
```

**Loading a full config block at startup:**

```python
def load_config() -> Validation[AppConfig, str]:
    host_v    = ValidateEnv("DB_HOST")
    port_v    = ValidateEnvInt("DB_PORT")
    debug_v   = ValidateEnvBool("DEBUG")
    workers_v = ValidateEnvInt("WORKERS").Then(Rule(lambda n: n >= 1, "WORKERS must be >= 1"))

    return (host_v & port_v & debug_v & workers_v).Map(
        lambda t: AppConfig(
            db_host=t[0][0][0],
            db_port=t[0][0][1],
            debug=t[0][1],
            workers=t[1],
        )
    )

match load_config():
    case Valid(value=cfg):
        start_app(cfg)
    case Invalid(errors=errs):
        for err in errs:
            print(f"Config error: {err}")
        sys.exit(1)
```

---

## Path validation

All functions in `monadical.validation.path`. Return `Validation[Path, str]`.

### `ValidateFile(path)`

Succeeds with a `Path` object if the path exists and is a regular file. Fails for directories, missing paths, or `None`.

```python
from pathlib import Path

ValidateFile("/etc/hosts")         # Valid(PosixPath('/etc/hosts'))
ValidateFile("/nonexistent")       # Invalid(["Not a valid file: '/nonexistent'"])
ValidateFile("/tmp")               # Invalid(["Not a valid file: '/tmp'"]) — is a directory
ValidateFile(None)                 # Invalid(["Not a valid file: None"])
ValidateFile(Path("/etc/hosts"))   # also accepts Path objects
```

### `ValidateDirectory(path)`

```python
ValidateDirectory("/tmp")            # Valid(PosixPath('/tmp'))
ValidateDirectory("/etc/hosts")      # Invalid(["Not a valid directory: '/etc/hosts'"]) — is a file
ValidateDirectory("/nonexistent")    # Invalid(["Not a valid directory: '/nonexistent'"])
ValidateDirectory(None)              # Invalid(["Not a valid directory: None"])
```

### `ValidateVisibleFile(path)`

Like `ValidateFile`, but also rejects files whose name starts with `.` (hidden files).

```python
ValidateVisibleFile("/etc/hosts")     # Valid(PosixPath('/etc/hosts'))
ValidateVisibleFile("/home/u/.bashrc") # Invalid(["Not a valid or visible file: ..."])
ValidateVisibleFile("/nonexistent")    # Invalid(["Not a valid or visible file: ..."])
```

---

## File I/O

All functions in `monadical.validation.io`. Return `Validation[T, str]`. They chain `ValidateFile` internally, so path errors and read errors both produce clear messages.

### `ReadText(path, encoding="utf-8")`

```python
ReadText("/etc/hosts")
# Valid('127.0.0.1 localhost\n...')

ReadText("/nonexistent")
# Invalid(["Not a valid file: '/nonexistent'"])

ReadText("/path/to/binary.bin", encoding="latin-1")
# Valid('...')
```

### `ReadBytes(path)`

```python
ReadBytes("/etc/hosts")
# Valid(b'127.0.0.1 localhost\n...')

ReadBytes(None)
# Invalid(["Not a valid file: None"])
```

### `ReadLines(path, encoding="utf-8", strip=False)`

Splits the file into a list of lines. With `strip=True`, strips whitespace from each line and removes blank lines.

```python
ReadLines("/etc/hosts")
# Valid(['127.0.0.1 localhost', '255.255.255.255 broadcasthost', ...])

ReadLines("/etc/hosts", strip=True)
# Valid(['127.0.0.1 localhost', '255.255.255.255 broadcasthost', ...])
# — blank lines and surrounding whitespace removed
```

### `ReadJson(path, encoding="utf-8")`

Reads and parses a JSON file in one step.

```python
ReadJson("/config/settings.json")
# Valid({'debug': False, 'port': 8080, ...})

ReadJson("/nonexistent.json")
# Invalid(["Not a valid file: '/nonexistent.json'"])

ReadJson("/config/broken.json")   # exists but invalid JSON
# Invalid(["ReadJson: failed to parse JSON from '/config/broken.json': ..."])
```

### `ParseJson(text)`

Parses a JSON string directly (no file I/O).

```python
ParseJson('{"key": "value"}')    # Valid({'key': 'value'})
ParseJson('[1, 2, 3]')           # Valid([1, 2, 3])
ParseJson('not json')            # Invalid(["ParseJson: invalid JSON: ..."])
ParseJson('{"unclosed": true')   # Invalid(["ParseJson: invalid JSON: ..."])
```

---

## Patterns and recipes

### Validating a form or request body

```python
from monadical.validation import Validation, Rule, Sequence
from monadical.validation import ParseInt, ParseUuid

def validate_create_order(body: dict) -> Validation[dict, str]:
    product_id_v = ParseUuid(body.get("product_id"))
    quantity_v   = (
        ParseInt(str(body.get("quantity", "")))
        .Then(Rule(lambda n: n >= 1,    "quantity must be at least 1"))
        .Then(Rule(lambda n: n <= 1000, "quantity cannot exceed 1000"))
    )
    note_v = (
        Validation.Require(body.get("note"), "note is required")
        .Then(Rule(lambda s: len(s) <= 500, "note cannot exceed 500 characters"))
    )

    return (product_id_v & quantity_v & note_v).Map(
        lambda t: {"product_id": str(t[0][0]), "quantity": t[0][1], "note": t[1]}
    )

result = validate_create_order({
    "product_id": "not-a-uuid",
    "quantity": "-5",
    "note": None,
})
# Invalid([
#   "ParseUuid: cannot parse 'not-a-uuid': ...",
#   "quantity must be at least 1",
#   "note is required",
# ])
```

### Building a library of reusable rules

```python
from monadical.validation import Rule, Validation, Validator

# Primitives
non_empty    = Rule(lambda s: bool(s and s.strip()), "Cannot be empty")
max_len      = lambda n: Rule(lambda s: len(s) <= n, f"Cannot exceed {n} characters")
min_len      = lambda n: Rule(lambda s: len(s) >= n, f"Must be at least {n} characters")
is_positive  = Rule(lambda n: n > 0,  "Must be positive")
in_range     = lambda lo, hi: Rule(lambda n: lo <= n <= hi, f"Must be between {lo} and {hi}")

# Composed validators
validate_username: Validator[str, str] = (
    Validation.Where(non_empty)
              .And(min_len(3))
              .And(max_len(30))
              .And(Rule(lambda s: s.isalnum(), "Must be alphanumeric"))
)

validate_password: Validator[str, str] = (
    Validation.Where(non_empty)
              .And(min_len(8))
              .And(Rule(lambda s: any(c.isupper() for c in s), "Must contain an uppercase letter"))
              .And(Rule(lambda s: any(c.isdigit() for c in s), "Must contain a digit"))
)

validate_age: Validator[str, int] = (
    Validation.Where(ParseInt)
              .Then(in_range(0, 120))
)
```

### Converting errors before returning to a caller

```python
from dataclasses import dataclass

@dataclass
class FieldError:
    field: str
    message: str

def validate_and_tag(field: str, value: str, validator) -> Validation[str, FieldError]:
    return validator(value).MapErrors(
        lambda msg: FieldError(field=field, message=msg)
    )

name_v  = validate_and_tag("name",  payload.get("name"),  validate_username)
email_v = validate_and_tag("email", payload.get("email"), validate_email)

result = name_v & email_v
# Invalid([FieldError(field='name', ...), FieldError(field='email', ...)])
```

### Bulk import with partial success

```python
from monadical.validation import Traverse, Partition

# Strict: all rows must be valid, report every error
def import_strict(rows: list[dict]) -> Validation[list[User], str]:
    return Traverse(rows, validate_row)

# Lenient: save what's valid, report what failed
def import_lenient(rows: list[dict]) -> tuple[list[User], list[str]]:
    return Partition(validate_row(r) for r in rows)

valid_users, errors = import_lenient(csv_rows)
if errors:
    print(f"Skipped {len(errors)} rows:")
    for err in errors:
        print(f"  {err}")
save_users(valid_users)
```

### Parsing and validating environment configuration

```python
from monadical.validation import ValidateEnvInt, ValidateEnv, ValidateEnvBool, Rule

log_level_v = (
    ValidateEnv("LOG_LEVEL")
    .Then(Rule(lambda s: s in {"DEBUG", "INFO", "WARNING", "ERROR"}, "Invalid log level"))
)

port_v = (
    ValidateEnvInt("PORT")
    .Then(Rule(lambda n: 1024 <= n <= 65535, "PORT must be between 1024 and 65535"))
)

workers_v = (
    ValidateEnvInt("WORKERS")
    .Then(Rule(lambda n: 1 <= n <= 32, "WORKERS must be between 1 and 32"))
)

config_v = log_level_v & port_v & workers_v
```

### Using `Sequence` vs `Traverse` vs `Partition` — when to reach for each

```python
# You have Validation values already — use Sequence
existing_results = [validate_field(f) for f in form_fields]
Sequence(existing_results)

# You have raw items and a validator function — use Traverse
Traverse(raw_items, validate_item)

# You want to split successes and failures (partial success is OK) — use Partition
good, bad = Partition(validate_item(x) for x in items)

# You want to silently discard failures — use Choose or Valids
valid_only = Choose(raw_items, validate_item)
valid_only = Valids(validate_item(x) for x in items)
```

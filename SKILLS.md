# Monadical — Skills Reference

A comprehensive guide to writing clean, pipeline-oriented code with the four monads in this library.
All types and functions use **PascalCase**. All variables use **camelCase**. All functions are **verb-driven**.
Boolean functions **answer a yes/no question** (e.g. `IsValid`, `HasErrors`, `IsSome`).

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Option — Optional Values](#2-option--optional-values)
3. [Result — Fallible Operations](#3-result--fallible-operations)
4. [Validation — Accumulated Errors](#4-validation--accumulated-errors)
5. [State — Stateful Computation](#5-state--stateful-computation)
6. [Operators Quick Reference](#6-operators-quick-reference)
7. [Combinators and Sequences](#7-combinators-and-sequences)
8. [Choosing the Right Monad](#8-choosing-the-right-monad)
9. [Cross-Monad Conversions](#9-cross-monad-conversions)
10. [Async Pipelines](#10-async-pipelines)
11. [Common Patterns and Recipes](#11-common-patterns-and-recipes)

---

## 1. Core Principles

### Pipelines, not imperative branches

The goal is to describe a sequence of transformations, not a tree of if/else. Every method returns a new monad, so operations chain naturally.

```python
# Bad — imperative, scattered error handling
def ProcessUser(userId: str) -> User:
    if userId is None:
        return None
    record = db.FindUser(userId)
    if record is None:
        return None
    if record.age < 18:
        return None
    return record

# Good — pipeline, every step is explicit
def ProcessUser(userId: str) -> Option[User]:
    return (
        Option.FromNullableString(userId)
        >> FindUser
        >> ValidateAge
    )
```

### Favour operators over verbose method calls

| Verbose                                | Operator                    | Meaning                    |
| -------------------------------------- | --------------------------- | -------------------------- |
| `option.Bind(f)`                       | `option >> f`               | Monadic bind               |
| `option.OrElse(lambda: fallback)`      | `option \| fallback`        | Fallback/alternative       |
| `validation1.Apply(validation2, pair)` | `validation1 & validation2` | Error-accumulating combine |

### Prefer `Match` for terminal decisions

Use `.Match(onSuccess, onFailure)` at the boundary where you must return a plain value. Keep monadic values inside pipelines for as long as possible.

```python
response = (
    Option.FromDict(data, "userId")
    >> FindUser
    >> BuildResponse
).Match(
    onSome  = lambda user: JsonResponse(user),
    onEmpty = lambda:      NotFoundResponse(),
)
```

---

## 2. Option — Optional Values

### When to use `Option`

Use `Option[T]` when:

- A value **may or may not exist**, and absence is not an error (no blame to assign)
- Reading from a dict, environment variable, nullable field, or config
- Implementing soft lookups where "not found" is a normal outcome
- Filtering a collection down to present values

Do **not** use `Option` when absence needs explanation — use `Result` or `Validation` instead.

### Constructors

```python
from option import Option

# Wrap a known value
someAge     = Option.Some(42)

# Wrap nothing
noAge       = Option.Empty()

# Convert from a nullable (None becomes Empty)
maybeEmail  = Option.FromNullable(user.email)

# Convert from a nullable string (also strips whitespace if asked)
maybeName   = Option.FromNullableString(raw, strip=True)

# Pull a value from a dict safely
maybeRole   = Option.FromDict(payload, "role")

# Conditional wrapping — value only if predicate is True
activeName  = Option.FromBool(user.isActive, user.name)

# Lazy conditional — factory only called when predicate is True
cachedItem  = Option.When(isCacheWarm, lambda: LoadFromCache(key))

# Wrap a call that might raise — silently becomes Empty on exception
parsed      = Option.Try(lambda: int(rawInput), ValueError)
```

### The `>>` bind operator

`>>` threads a value through a chain of functions that each return an `Option`. If any step returns `Empty`, the rest of the chain is skipped.

```python
def FindUser(userId: str) -> Option[User]: ...
def FindProfile(user: User) -> Option[Profile]: ...
def FindAvatar(profile: Profile) -> Option[str]: ...

avatarUrl = (
    Option.FromNullableString(rawId)
    >> FindUser
    >> FindProfile
    >> FindAvatar
)
```

Each function **must** accept the unwrapped value and **must** return an `Option`. This is the key contract of `>>`.

### The `|` alternative operator

`|` provides a fallback when the left side is `Empty`.

```python
# Static fallback value
displayName = maybeName | Option.Some("Anonymous")

# Lazy fallback — lambda is only called if left is Empty
configValue = GetEnv("TIMEOUT") | (lambda: Option.Some("30"))

# Chain of fallbacks
userId = (
    Option.FromDict(request.headers, "X-User-Id")
    | (lambda: Option.FromDict(request.cookies, "userId"))
    | (lambda: Option.Some(GUEST_ID))
)
```

### Map vs Bind

- `Map` — transform the inner value, stay wrapped. Use when `func` returns a plain value.
- `Bind` (or `>>`) — chain to another step that returns an `Option`. Use when `func` returns an `Option`.

```python
# Map: str -> str, stays Option[str]
upperName = maybeName.Map(lambda name: name.upper())

# Bind: str -> Option[User], steps into the next Option
maybeUser = maybeId >> FindUser

# Wrong: using Map with a function that returns Option creates Option[Option[T]]
broken = maybeName.Map(lambda name: FindUser(name))  # Option[Option[User]] — avoid
```

When you accidentally nest, use `.Flatten()` to unwrap one layer.

### Filtering

```python
# Keep the value only if the predicate holds
positiveAge = someAge.Filter(lambda age: age > 0)

# Composed: parse then filter
maybeAge = (
    Option.FromNullableString(rawAge)
    >> ParseInt
    >> (lambda age: Option.FromBool(age >= 0, age))
)
```

### Pattern matching

`Match` is the clean way to exit the monad. It is **exhaustive** — both cases must be handled.

```python
message = maybeUser.Match(
    onSome  = lambda user: f"Welcome back, {user.name}!",
    onEmpty = lambda:      "Please log in.",
)
```

### Extraction methods

Only extract when you are at the boundary of the monadic world.

```python
# Safe — provide a fallback
timeout = GetEnvInt("TIMEOUT").IfEmptyValue(30)

# Safe — use a factory fallback
conn    = maybeConn.IfEmpty(lambda: CreateConnection())

# Unsafe — raises ValueError if Empty; use only when Empty is truly impossible
value   = option.Unwrap()

# Convert for external APIs
nullable = option.ToNullable()   # T | None
asList   = option.ToList()       # [] or [value]
```

### Side effects with `Tap`

`Tap` lets you observe the value mid-pipeline without altering the chain.

```python
result = (
    Option.FromDict(cache, key)
    .Tap(lambda v: logger.debug(f"Cache hit: {v}"))
    .TapEmpty(lambda: logger.debug("Cache miss"))
    >> ComputeValue
)
```

### Combining multiple Options

```python
from option import Sequence, Traverse, Choose, Somes, Partition

# Zip two Options into a tuple — Empty if either is Empty
pair = nameOption.Zip(ageOption)   # Option[tuple[str, int]]

# Combine N options — Empty if any is Empty
all3 = Option.All(opt1, opt2, opt3)   # Option[tuple[T1, T2, T3]]

# Map2: combine two options with a function
fullName = firstOption.Map2(lastOption, lambda f, l: f"{f} {l}")

# Sequence a list — Empty if any element is Empty
maybeAll = Sequence([opt1, opt2, opt3])   # Option[list[T]]

# Traverse: map and sequence
maybeInts = Traverse(rawStrings, ParseInt)   # Option[list[int]]

# Choose: filter-map, discards Empty results
validInts = Choose(rawStrings, ParseInt)     # list[int]

# Somes: extract values, discarding Empty
values = Somes([opt1, opt2, opt3])           # list[T]

# Partition: split into values and count of Empty
values, emptyCount = Partition([opt1, opt2, opt3])
```

### Parsing utilities

```python
from option import ParseInt, ParseFloat, ParseDate, ParseUuid, ParseBool, ParseEnum

age   = ParseInt("42")          # Option[int]
score = ParseFloat("3.14")      # Option[float]
dob   = ParseDate("1990-01-01") # Option[date]
uid   = ParseUuid(rawId)        # Option[UUID]

from option import GetEnv, GetEnvInt
debug = GetEnvBool("DEBUG")     # Option[bool]
port  = GetEnvInt("PORT")       # Option[int]
```

### Path and I/O utilities

```python
from option import AsFile, AsDirectory, ReadText, ReadJson

config     = AsFile("/etc/app/config.yaml") >> ReadText     # Option[str]
jsonData   = AsFile(rawPath) >> ReadJson                    # Option[Any]
```

### Boolean query methods

```python
option.IsSome()                         # True if value is present
option.IsEmpty()                        # True if absent
option.Exists(lambda v: v > 10)         # True if Some and predicate holds
option.ForAll(lambda v: v > 10)         # True if Empty or predicate holds
option.Contains(42)                     # True if Some(42)
```

### Complete example — user profile lookup

```python
from option import Option, ParseUuid, GetEnv

def ResolveProfilePicture(rawId: str) -> str:
    fallbackUrl = GetEnv("DEFAULT_AVATAR").IfEmptyValue("/static/default.png")

    return (
        Option.FromNullableString(rawId, strip=True)
        >> ParseUuid
        >> FindUser
        >> (lambda user: Option.FromNullable(user.profile))
        >> (lambda profile: Option.FromNullableString(profile.avatarUrl))
        | (lambda: Option.Some(fallbackUrl))
    ).Unwrap()
```

---

## 3. Result — Fallible Operations

### When to use `Result`

Use `Result[T]` when:

- An operation **can fail**, and the failure carries **diagnostic information** (an exception)
- Replacing `try/except` blocks in pipelines
- Calling external services, databases, or parsing user input where errors must propagate
- There is exactly **one failure mode** per operation (contrast with `Validation`)

`Result` short-circuits on the first failure, like a railway track with a single error lane.

### Constructors

```python
from result import Result

# Wrap a success
okAge      = Result.Success(42)

# Wrap a failure
failAge    = Result.Fail(ValueError("Age must be positive"))

# Fail if value is None
userResult = Result.SuccessNonNull(db.FindById(userId))

# Capture a call that might raise
parsed     = Result.Try(
    lambda: int(rawInput),
    lambda e: ValueError(f"Cannot parse age: {e}"),
)

# Combine multiple Results — fails on first Failure
combined   = Result.All(nameResult, ageResult, emailResult)
```

### The `>>` bind operator

```python
def ParseUserId(raw: str) -> Result[UUID]: ...
def FetchUser(uid: UUID) -> Result[User]: ...
def AuthoriseAccess(user: User) -> Result[User]: ...

authorisedUser = (
    Result.Try(lambda: raw.strip(), lambda e: ValueError(str(e)))
    >> ParseUserId
    >> FetchUser
    >> AuthoriseAccess
)
```

The first `Failure` terminates the chain. All subsequent steps are skipped.

### The `|` alternative operator

```python
# Try primary source, fall back to secondary
userData = FetchFromCache(userId) | (lambda: FetchFromDatabase(userId))

# Chain of fallbacks
config = (
    ReadJson(primaryPath)
    | (lambda: ReadJson(fallbackPath))
    | (lambda: Result.Success(DEFAULT_CONFIG))
)
```

### Map vs Bind

Same rule as `Option`:

- `Map` — plain transform, exceptions are caught and become `Failure`
- `Bind` (or `>>`) — chains to another `Result`-returning step

```python
# Map: int -> int, exception-safe
doubled = ageResult.Map(lambda age: age * 2)

# Bind (>>): int -> Result[Profile]
profile = ageResult >> LookupProfile

# MapError: transform the error type
mapped = result.MapError(lambda e: AppError(str(e)))
```

### Recovery

```python
# Recover with a function of the error
value = result.Recover(lambda e: DEFAULT_VALUE)

# Recover with a static value
value = result.RecoverValue(DEFAULT_VALUE)

# OrElse: recover with another Result-producing function
value = result.OrElse(lambda: FetchFromFallback())
```

### Pattern matching

```python
response = authorisedUser.Match(
    onSuccess = lambda user: JsonResponse(user.ToDict()),
    onFailure = lambda err:  ErrorResponse(str(err)),
)
```

### Extraction

```python
# Safe — provide error fallback
age   = ageResult.IfFailValue(0)
age   = ageResult.IfFail(lambda e: ComputeDefault(e))

# Unsafe — raises the wrapped exception; use only at program boundaries
value = result.Unwrap() if result.IsSuccess() else None

# Convert
opt   = result.ToNullable()   # T | None
lst   = result.ToList()       # [] or [value]
```

### Side effects

```python
processed = (
    FetchData(url)
    .Tap(lambda data: logger.info(f"Fetched {len(data)} bytes"))
    .TapFail(lambda e: logger.error(f"Fetch failed: {e}"))
    >> ParseJson
    >> ValidateSchema
)
```

### HTTP integration

```python
from result import FromStatusCode, HttpError

def CallApi(endpoint: str) -> Result[dict]:
    resp = requests.get(endpoint)
    return (
        FromStatusCode(resp.status_code, resp.json(), resp.reason)
        >> ParseBody
    )
```

`FromStatusCode` maps 2xx to `Ok`, everything else to `Failure[HttpError]`.

### Environment and parsing

```python
from result import RequireEnv, RequireEnvInt, ParseInt, ParseDate

port       = RequireEnvInt("PORT")              # Result[int]
dbUrl      = RequireEnv("DATABASE_URL")         # Result[str]
startDate  = ParseDate(rawDate)                 # Result[date]
```

### Combining multiple Results

```python
from result import Sequence, Traverse, Partition, Choose, Oks

# Sequence — fails on first failure
allResults = Sequence([res1, res2, res3])    # Result[list[T]]

# Traverse — map then sequence
parsedInts = Traverse(rawStrings, ParseInt)  # Result[list[int]]

# Partition — separate successes from failures
values, errors = Partition([res1, res2, res3])

# Choose — keep only successes
validValues = Choose(rawStrings, ParseInt)   # list[int]

# Oks — extract successes, ignore failures
values = Oks([res1, res2, res3])             # list[T]
```

### Boolean queries

```python
result.IsSuccess()                      # True if Ok
result.IsFailure()                      # True if Failure
result.Exists(lambda v: v > 0)          # True if Ok and predicate holds
result.ForAll(lambda v: v > 0)          # True if Failure or predicate holds
result.Contains(42)                     # True if Ok(42)
```

### Complete example — API request pipeline

```python
from result import Result, RequireEnv, ParseJson, ReadJson
from result import FromStatusCode

def FetchConfig(environment: str) -> Result[AppConfig]:
    return (
        RequireEnv("CONFIG_URL")
        >> (lambda baseUrl: Result.Try(
            lambda: requests.get(f"{baseUrl}/{environment}"),
            lambda e: ConnectionError(f"Config fetch failed: {e}"),
        ))
        >> (lambda resp: FromStatusCode(resp.status_code, resp.text))
        >> ParseJson
        >> (lambda data: Result.Try(
            lambda: AppConfig(**data),
            lambda e: ValueError(f"Invalid config shape: {e}"),
        ))
    )

config = FetchConfig("production").IfFail(
    lambda e: (logger.error(str(e)), DEFAULT_CONFIG)[1]
)
```

---

## 4. Validation — Accumulated Errors

### When to use `Validation`

Use `Validation[T, E]` when:

- You need to **collect all errors** rather than stopping at the first
- Validating a form, request body, or domain object where the user benefits from seeing every problem at once
- Composing multiple independent validation rules against the same input
- The error type `E` should be a human-readable string or a domain-specific error object

`Validation` is **not** a drop-in for `Result`. It uses applicative composition (`&`, `Apply`) rather than monadic bind when you want error accumulation. Use `Then` only when later validations depend on earlier ones (which will short-circuit).

### Constructors

```python
from validation import Validation

# Wrap a success
validAge    = Validation.Success(42)

# Wrap failures (always a list of errors)
invalidAge  = Validation.Fail(["Age is required", "Age must be a number"])

# Fail if None
nameResult  = Validation.Require(user.name, "Name is required")

# Capture a throwing call, map exception to error list
parsed      = Validation.Try(
    lambda: int(rawAge),
    lambda e: [f"Age must be a number, got: {rawAge}"],
)
```

### Applicative composition — the `&` operator

The `&` operator is what makes `Validation` special. It **accumulates errors from both sides**, so the caller sees everything at once.

```python
# Both validations run; errors from both are combined if either fails
nameAndAge = ValidateName(name) & ValidateAge(age)
# nameAndAge is Validation[tuple[str, int], str]

# Build a full object by chaining &
userValidation = (
    ValidateName(rawName)
    & ValidateEmail(rawEmail)
    & ValidateAge(rawAge)
    & ValidateRole(rawRole)
)
# type: Validation[tuple[tuple[tuple[str, str], int], str], str]
```

Use `.MapN` to collapse the nested tuple into a useful shape:

```python
userResult = (
    ValidateName(rawName) & ValidateEmail(rawEmail) & ValidateAge(rawAge)
).MapN(lambda name, email, age: User(name=name, email=email, age=age))
```

### Monadic bind with `Then`

`Then` short-circuits like `Result`. Use it when a later validation **depends on** an earlier result.

```python
# Parse first, then validate the parsed value
ageValidation = (
    Validation.Try(lambda: int(rawAge), lambda e: ["Age must be a number"])
    .Then(lambda age: Validation.Success(age) if age >= 0 else Validation.Fail(["Age must be non-negative"]))
)
```

### Building reusable validators with `Rule` and `Validator`

```python
from validation import Validation, Rule

# Rule: predicate -> error -> validator function
IsNonEmpty  = Rule(lambda s: bool(s.strip()), "Must not be blank")
IsShortEnough = Rule(lambda s: len(s) <= 100, "Must be 100 characters or fewer")

# Validator: composable chain of rules
from validation import Validation

NameValidator = (
    Validation.Where(IsNonEmpty)
    .And(IsShortEnough)
)

# Apply to a value
nameResult = NameValidator(rawName)   # Validation[str, str]
```

`Validator.And` runs the next rule only if the previous passed. To check all rules independently, use `&` between `Validation` values.

### Pattern matching

```python
output = userValidation.Match(
    on_ok    = lambda user: f"Created user {user.name}",
    on_error = lambda errs: "Errors:\n" + "\n".join(f"  • {e}" for e in errs),
)
```

### Extraction

```python
# Safe — fallback from error list
user = validated.GetOrElse(lambda errors: GuestUser())

# Safe — static default
user = validated.GetOr(DEFAULT_USER)

# Unsafe — raises ValueError with errors; only at confirmed-valid boundaries
user = validated.Unwrap()
```

### Side effects

```python
processed = (
    ValidateRequest(payload)
    .Tap(lambda req: auditLog.Record(req))
    .TapErrors(lambda errs: logger.warning(f"Validation failed: {errs}"))
)
```

### Converting to other monads

```python
# To Option — loses error details
maybeUser = validated.ToOption()

# To Result — provide a mapper from error list to exception
resultUser = validated.ToResult(
    lambda errors: ValueError("; ".join(errors))
)
```

### Error accumulation across collections

```python
from validation import Sequence, Traverse, Partition, Choose

# Validate each item; accumulate ALL errors across ALL items
allValid = Sequence([ValidateItem(x) for x in items])

# Traverse: map + sequence
allValid = Traverse(items, ValidateItem)   # Validation[list[T], E]

# Partition: separate valid values from all collected errors
values, allErrors = Partition([ValidateItem(x) for x in items])

# Choose: keep only valid values, silently drop invalid
validItems = Choose(items, ValidateItem)   # list[T]
```

### Boolean queries

```python
v.IsOk()                            # True if Valid
v.HasErrors()                       # True if Invalid
v.Exists(lambda x: x > 0)          # True if Valid and predicate holds
v.ForAll(lambda x: x > 0)          # True if Invalid or predicate holds
```

### Complete example — form validation

```python
from validation import Validation, Rule, ParseInt, ValidateEnv

IsNonEmpty     = Rule(lambda s: bool(s and s.strip()),      "Must not be blank")
IsValidEmail   = Rule(lambda s: "@" in s and "." in s,      "Must be a valid email")
IsAdult        = Rule(lambda n: n >= 18,                    "Must be 18 or older")
IsReasonableAge = Rule(lambda n: n <= 120,                  "Unrealistic age")

def ValidateName(raw: str) -> Validation[str, str]:
    return Validation.Where(IsNonEmpty)(raw)

def ValidateEmail(raw: str) -> Validation[str, str]:
    return (
        Validation.Where(IsNonEmpty)
        .And(IsValidEmail)
    )(raw)

def ValidateAge(raw: str) -> Validation[int, str]:
    return (
        ParseInt(raw)
        .Then(lambda age: (
            Validation.Where(IsAdult)
            .And(IsReasonableAge)
        )(age))
    )

def ValidateRegistration(data: dict) -> Validation[NewUser, str]:
    return (
        ValidateName(data.get("name", ""))
        & ValidateEmail(data.get("email", ""))
        & ValidateAge(data.get("age", ""))
    ).MapN(lambda name, email, age: NewUser(name=name, email=email, age=age))
```

---

## 5. State — Stateful Computation

### When to use `State`

Use `State[S, A]` when:

- A computation **reads from and/or writes to** shared state, and you want to keep that state explicit
- Building interpreters, configuration systems, counters, or accumulation pipelines
- You want pure, testable functions that thread state without global variables or mutation
- Implementing game logic, simulations, or config builders where step order matters

`State[S, A]` is a **description** of a computation — it does nothing until you call `.Run(initialState)`.

### The State contract

```
State[S, A] wraps:  S -> (A, S)
                         ↑    ↑
                       value  new state
```

A `State` computation takes an input state, produces a value, and returns the next state.

### Constructors

```python
from state import State

# Return a value without touching state
pure = State.Of(42)                     # State[S, int]

# Read the current state as the value
getState = State.Get()                  # State[S, S]

# Replace the state entirely
setState = State.Put(newState)          # State[S, None]

# Modify state with a function
increment = State.Modify(lambda s: s + 1)   # State[int, None]

# Extract a value from state without changing it
getName = State.Gets(lambda s: s.name)  # State[Config, str]

# Conditionally execute a stateful action
conditionalIncrement = State.When(
    lambda s: s < 10,
    State.Modify(lambda s: s + 1),
)
```

### The `>>` bind operator

`>>` sequences stateful computations. The output value of one step becomes the input to the next function.

```python
counter = (
    State.Get()
    >> (lambda current: State.Put(current + 1))
    >> (lambda _: State.Get())
)

value, finalState = counter.Run(0)   # value=1, finalState=1
```

### Map and Bind

```python
# Map: transform the value, state is unaffected
doubled = State.Gets(lambda s: s.count).Map(lambda n: n * 2)

# Bind (>>): value flows into the next stateful function
pipeline = State.Get() >> ComputeNext >> ApplyToState
```

### `Then` — discard intermediate value

When you want to sequence effects but don't care about the intermediate value:

```python
pipeline = (
    State.Put(INITIAL)
    .Then(State.Modify(Normalise))
    .Then(State.Modify(EnrichWithDefaults))
    .Then(State.Get())
)
```

### Running the computation

```python
value, state = pipeline.Run(initialState)   # full result
value         = pipeline.Eval(initialState) # value only
state         = pipeline.Exec(initialState) # state only
```

### Zoom — operating on nested state

`Zoom` lets a computation that knows about a small piece of state (`S`) work inside a computation that carries a larger state (`BigS`).

```python
def IncrementCounter(state: State[int, None]) -> State[AppState, None]:
    return state.Zoom(
        getter = lambda appState: appState.counter,
        setter = lambda appState, counter: AppState(
            counter  = counter,
            config   = appState.config,
        ),
    )

fullPipeline = IncrementCounter(State.Modify(lambda n: n + 1))
```

### Local — temporarily modified state

`Local` runs a computation with a modified state, then **restores** the original state afterwards. The value produced is kept.

```python
# Run computation in a context with logging enabled, restore afterwards
withLogging = computeResult.Local(lambda s: Config(s, debug=True))
```

### Tap — side effects without changing state or value

```python
withLogging = (
    State.Get()
    .TapState(lambda s: logger.debug(f"State: {s}"))
    .Tap(lambda v: logger.debug(f"Value: {v}"))
    >> ProcessValue
)
```

### Combining multiple State computations

```python
from state import Sequence, Traverse, Replicate

# Run a list of stateful computations in order, collect values
allValues = Sequence([step1, step2, step3])    # State[S, list[A]]

# Map items to stateful computations, run all in order
allResults = Traverse(items, ProcessItem)      # State[S, list[B]]

# Run the same computation N times, collect results
history = Replicate(5, State.Modify(lambda s: s + 1).Then(State.Get()))
```

### Complete example — config builder

```python
from state import State
from typing import NamedTuple

class Config(NamedTuple):
    host:    str  = "localhost"
    port:    int  = 8080
    debug:   bool = False
    timeout: int  = 30

def SetHost(host: str) -> State[Config, None]:
    return State.Modify(lambda cfg: cfg._replace(host=host))

def SetPort(port: int) -> State[Config, None]:
    return State.Modify(lambda cfg: cfg._replace(port=port))

def EnableDebug() -> State[Config, None]:
    return State.Modify(lambda cfg: cfg._replace(debug=True))

def BuildConfig(overrides: dict) -> Config:
    pipeline = (
        SetHost(overrides.get("host", "localhost"))
        .Then(SetPort(overrides.get("port", 8080)))
        .Then(EnableDebug() if overrides.get("debug") else State.Of(None))
        .Then(State.Get())
    )
    return pipeline.Eval(Config())
```

### Complete example — stateful counter with conditional logic

```python
from state import State

AddOne    = State.Modify(lambda n: n + 1)
ResetWhen = lambda limit: State.When(lambda n: n >= limit, State.Put(0))

counter = (
    AddOne
    .Then(ResetWhen(10))
    .Then(State.Get())
)

for tick in range(25):
    value, state = counter.Run(state if tick > 0 else 0)
    print(f"tick={tick}, counter={value}")
```

---

## 6. Operators Quick Reference

### `>>` — Bind (all monads)

Threads the unwrapped value into the next function. Short-circuits on `Empty` / `Failure`.

```python
option >> funcReturningOption    # Option[U]
result >> funcReturningResult    # Result[U]
state  >> funcReturningState     # State[S, B]
```

The function on the right **must** return the same monad type.

### `|` — Alternative / Fallback (Option and Result)

```python
# Returns left if Some/Ok, otherwise evaluates right
option | Option.Some(default)
option | (lambda: ComputeFallback())    # lazy

result | Result.Success(default)
result | (lambda: TryAlternative())
```

Use a lambda on the right side whenever the fallback is expensive or has side effects — it will only be evaluated if needed.

### `&` — Applicative combine (Validation only)

```python
# Both sides always evaluated; errors from both accumulated
v1 & v2     # Validation[tuple[T1, T2], E]
v1 & v2 & v3  # Validation[tuple[tuple[T1, T2], T3], E]
```

Use `.MapN(lambda a, b, c: ...)` after `&` chains to unpack the nested tuple into a clean object.

### Operator chaining idioms

```python
# Option: short-circuit lookup pipeline
result = (
    Option.FromNullableString(raw)
    >> ParseUuid
    >> FindById
    >> (lambda entity: Option.FromNullable(entity.activeVersion))
    | (lambda: Option.Some(DEFAULT_VERSION))
)

# Result: API call with fallback
data = (
    FetchPrimary(url)
    | (lambda: FetchMirror(mirrorUrl))
    | (lambda: Result.Success(CACHED_DATA))
)

# Validation: accumulate all field errors
validated = (
    ValidateField1(data["f1"])
    & ValidateField2(data["f2"])
    & ValidateField3(data["f3"])
).MapN(lambda f1, f2, f3: DomainObject(f1, f2, f3))

# State: thread state through multiple steps
finalState = (
    State.Modify(Initialise)
    .Then(State.Modify(ApplyDefaults))
    .Then(State.Modify(EnrichFromEnv))
    .Then(State.Get())
).Eval(EmptyConfig())
```

---

## 7. Combinators and Sequences

All four monads expose a consistent set of combinators for working with collections.

### `Sequence` — all-or-nothing collection processing

```python
from option     import Sequence as OptionSequence
from result     import Sequence as ResultSequence
from validation import Sequence as ValidationSequence
from state      import Sequence as StateSequence

# Option: Empty if any element is Empty
maybeAll = OptionSequence([opt1, opt2, opt3])

# Result: fails on the first Failure
allResults = ResultSequence([res1, res2, res3])

# Validation: accumulates ALL errors
allValidated = ValidationSequence([val1, val2, val3])

# State: runs all in sequence, collects values
allStates = StateSequence([state1, state2, state3])
```

The key difference: `Validation.Sequence` accumulates all errors; `Result.Sequence` stops at the first failure.

### `Traverse` — map then sequence

Equivalent to `Sequence(list(map(func, items)))` but more efficient.

```python
from option     import Traverse as OptionTraverse
from result     import Traverse as ResultTraverse
from validation import Traverse as ValidationTraverse
from state      import Traverse as StateTraverse

parsedInts = ResultTraverse(rawStrings, ParseInt)   # Result[list[int]]
```

### `Choose` — filter-map (keep successes only)

When you want only the successful results and are happy to silently discard failures:

```python
from option     import Choose as OptionChoose
from result     import Choose as ResultChoose
from validation import Choose as ValidationChoose

validInts = ResultChoose(rawStrings, ParseInt)   # list[int]
```

### `Partition` — separate successes from failures

```python
from option     import Partition as OptionPartition
from result     import Partition as ResultPartition
from validation import Partition as ValidationPartition

# Option
values, emptyCount = OptionPartition([opt1, opt2, opt3])

# Result
values, errors = ResultPartition([res1, res2, res3])

# Validation
values, allErrors = ValidationPartition([val1, val2, val3])
# allErrors is a flat list of ALL errors from ALL invalid items
```

### `Somes` / `Oks` / `Valids` — extract successes

```python
from option     import Somes
from result     import Oks
from validation import Valids

presentValues = Somes([opt1, opt2, opt3])   # list[T]
successValues = Oks([res1, res2, res3])     # list[T]
validValues   = Valids([val1, val2, val3])  # list[T]
```

---

## 8. Choosing the Right Monad

| Scenario                                     | Use                                |
| -------------------------------------------- | ---------------------------------- |
| Value might not exist; absence is normal     | `Option`                           |
| Operation might fail; one failure mode       | `Result`                           |
| Validating input; want all errors at once    | `Validation`                       |
| Computation threads shared state             | `State`                            |
| Reading optional config / env vars           | `Option`                           |
| Required config / env vars                   | `Result`                           |
| Validating a form or request body            | `Validation`                       |
| Calling an API that can fail                 | `Result`                           |
| Building a config object step by step        | `State`                            |
| Filter-mapping a collection                  | `Option.Choose` or `Result.Choose` |
| Batch-validate a collection                  | `Validation.Sequence`              |
| Sequential steps with shared mutable context | `State`                            |

### Decision tree

```
Is the value optional with no blame?
  YES → Option
  NO  → Is there exactly one failure mode?
          YES → Does computation thread state?
                  YES → State
                  NO  → Result
          NO  → Do you need to accumulate all errors?
                  YES → Validation
                  NO  → Result
```

### Option vs Result

```python
# Option: "the key might not be there, that's fine"
maybeRole = Option.FromDict(user, "role")

# Result: "the key must be there, missing is a bug"
roleResult = Result.SuccessNonNull(user.get("role")) \
    .MapError(lambda _: KeyError("role is required"))
```

### Result vs Validation

```python
# Result: parse one value — stops at first error
ageResult = ParseInt(raw) >> ValidatePositive

# Validation: validate many fields — accumulates all errors
formResult = (
    ValidateName(data["name"])
    & ValidateEmail(data["email"])
    & ValidateAge(data["age"])
).MapN(NewUser)
```

---

## 9. Cross-Monad Conversions

```python
from convert import OptionToResult, ResultToOption
from option  import Option
from result  import Result

# Option -> Result: must supply an error for the Empty case
result   = OptionToResult(maybeUser, KeyError("User not found"))

# Result -> Option: failure detail is discarded
option   = ResultToOption(userResult)

# Validation -> Option
option   = validated.ToOption()

# Validation -> Result: must supply error mapper
result   = validated.ToResult(lambda errors: ValueError("; ".join(errors)))

# Result -> Option inline
option   = result.ToNullable()
option   = Option.FromNullable(result.ToNullable())
```

### When to convert

- Convert `Option → Result` when you reach a layer that requires error context
- Convert `Result → Option` when you are aggregating and don't need per-item errors
- Convert `Validation → Result` at the boundary to business logic that uses `Result`
- Avoid converting back and forth in the middle of a pipeline — pick the right monad at the start

---

## 10. Async Pipelines

All three primary monads (`Option`, `Result`, `Validation`) support async variants of `Map`, `Bind`, and `Match`.

```python
import asyncio

# Option async pipeline
async def ResolveUser(rawId: str) -> Option[User]:
    return await (
        Option.FromNullableString(rawId)
        >> ParseUuid
    ).MapAsync(FetchUserAsync)

# Result async pipeline
async def ProcessOrder(orderId: str) -> Result[Receipt]:
    return await (
        ParseUuid(orderId)
        >> FetchOrderAsync
    ).BindAsync(ChargePaymentAsync)

# Match async
async def HandleRequest(rawId: str) -> Response:
    return await ResolveUser(rawId).MatchAsync(
        onSome  = lambda user: BuildResponseAsync(user),
        onEmpty = lambda:      asyncio.coroutine(lambda: NotFoundResponse())(),
    )
```

### Async naming conventions

| Sync                | Async                  |
| ------------------- | ---------------------- |
| `Map(func)`         | `MapAsync(asyncFunc)`  |
| `Bind(func)` / `>>` | `BindAsync(asyncFunc)` |
| `Match(onA, onB)`   | `MatchAsync(onA, onB)` |

Note: `>>` does not have an async variant — use `.BindAsync()` explicitly for async steps.

---

## 11. Common Patterns and Recipes

### Recipe 1 — Safe dict extraction pipeline

```python
def ExtractConfig(raw: dict) -> Result[ServerConfig]:
    return (
        Result.SuccessNonNull(raw.get("server"))
        .MapError(lambda _: KeyError("'server' block is required"))
        >> (lambda server: Result.All(
            Result.SuccessNonNull(server.get("host"))
                .MapError(lambda _: ValueError("host is required")),
            ParseInt(str(server.get("port", ""))),
        ))
        >> (lambda pair: Result.Success(
            ServerConfig(host=pair[0], port=pair[1])
        ))
    )
```

### Recipe 2 — Nullable → pipeline → response

```python
def GetUserResponse(rawId: str | None) -> HttpResponse:
    return (
        Option.FromNullableString(rawId, strip=True)
        >> ParseUuid
        >> FindUser
    ).Match(
        onSome  = lambda user: OkResponse(user.ToDict()),
        onEmpty = lambda:      NotFoundResponse(),
    )
```

### Recipe 3 — Form validation with structured errors

```python
from validation import Validation, Rule, ParseInt

IsPresent   = Rule(lambda s: bool(s and s.strip()), "is required")
IsEmail     = Rule(lambda s: "@" in s,              "must be a valid email address")
IsAdult     = Rule(lambda n: n >= 18,               "must be at least 18")

def ValidateSignup(form: dict) -> Validation[NewUser, str]:
    nameV  = Validation.Where(IsPresent)(form.get("name", ""))
    emailV = (Validation.Where(IsPresent).And(IsEmail))(form.get("email", ""))
    ageV   = ParseInt(form.get("age", "")).Then(
        lambda age: Validation.Where(IsAdult)(age)
    )
    return (nameV & emailV & ageV).MapN(
        lambda name, email, age: NewUser(name=name, email=email, age=age)
    )
```

### Recipe 4 — Batch processing with error collection

```python
from result import Traverse, Partition, ParseInt

def ProcessBatch(rawItems: list[str]) -> tuple[list[int], list[Exception]]:
    results = [ParseInt(item) for item in rawItems]
    values, errors = Partition(results)
    return values, errors

# Or: stop on first error
def RequireAllValid(rawItems: list[str]) -> Result[list[int]]:
    return Traverse(rawItems, ParseInt)
```

### Recipe 5 — State-threaded configuration

```python
from state import State
from os import environ

def LoadConfig() -> AppConfig:
    def ApplyEnvOverrides(cfg: AppConfig) -> AppConfig:
        return cfg._replace(
            host  = environ.get("HOST",  cfg.host),
            port  = int(environ.get("PORT", cfg.port)),
            debug = environ.get("DEBUG", "").lower() == "true",
        )

    pipeline = (
        State.Of(AppConfig())
        .Then(State.Modify(LoadDefaults))
        .Then(State.Modify(ApplyEnvOverrides))
        .Then(State.Modify(Validate))
        .Then(State.Get())
    )

    return pipeline.Eval(AppConfig())
```

### Recipe 6 — Fallback chain with lazy evaluation

```python
def GetConnectionString() -> Result[str]:
    return (
        RequireEnv("DATABASE_URL")
        | (lambda: RequireEnv("DB_URL"))
        | (lambda: (
            RequireEnv("DB_HOST")
            >> (lambda host: Result.Success(f"postgresql://{host}/app"))
        ))
    )
```

### Recipe 7 — Converting between monads at service boundaries

```python
# Service layer returns Result
def FetchUserService(userId: UUID) -> Result[User]: ...

# Controller wants Option (maps to 404 vs 500 separately)
def GetUserHandler(rawId: str) -> HttpResponse:
    maybeUser = (
        Option.FromNullableString(rawId)
        >> ParseUuid
        >> (lambda uid: ResultToOption(FetchUserService(uid)))
    )
    return maybeUser.Match(
        onSome  = lambda user: OkResponse(user),
        onEmpty = lambda:      NotFoundResponse(),
    )
```

### Recipe 8 — Tap for observability without breaking the pipeline

```python
def ProcessPayment(order: Order) -> Result[Receipt]:
    return (
        ValidateOrder(order)
        .Tap(lambda o: metrics.Increment("orders.validated"))
        .TapFail(lambda e: metrics.Increment("orders.validation_failed"))
        >> ChargeCard
        .Tap(lambda receipt: auditLog.Write(receipt))
        .TapFail(lambda e: alerting.Fire(PaymentFailedAlert(order, e)))
        >> IssueReceipt
    )
```

### Recipe 9 — Zip for combining independent optional values

```python
def BuildDisplayName(user: User) -> str:
    return (
        Option.FromNullable(user.firstName)
        .Zip(Option.FromNullable(user.lastName))
        .Map(lambda pair: f"{pair[0]} {pair[1]}")
        | Option.FromNullable(user.username)
        | Option.Some("Anonymous")
    ).Unwrap()
```

### Recipe 10 — Replicate for repeated stateful steps

```python
from state import Replicate, State

# Generate 5 unique IDs using a counter as state
GenerateId = State.Gets(lambda n: f"item-{n:04d}").Tap(
    lambda _: None
) >> (lambda id: State.Modify(lambda n: n + 1).Then(State.Of(id)))

ids, _ = Replicate(5, GenerateId).Run(1)
# ids = ["item-0001", "item-0002", ..., "item-0005"]
```

---

## Naming Quick Reference

| Category                   | Convention                | Example                                                               |
| -------------------------- | ------------------------- | --------------------------------------------------------------------- |
| Types                      | PascalCase                | `Option`, `Result`, `Validation`, `State`, `User`, `Config`           |
| Functions                  | PascalCase, verb-first    | `FindUser`, `ParseAge`, `ValidateEmail`, `BuildConfig`                |
| Boolean functions          | PascalCase, question form | `IsSome`, `IsEmpty`, `HasErrors`, `IsSuccess`, `IsFailure`, `IsAdult` |
| Variables                  | camelCase                 | `rawId`, `maybeUser`, `userResult`, `parsedAge`                       |
| Lambdas (inline)           | camelCase parameter names | `lambda userId: ...`, `lambda err: ...`                               |
| Predicates passed to rules | PascalCase                | `IsNonEmpty`, `IsValidEmail`, `IsAdult`                               |
| No abbreviations ever      | Over all Rule             | `cxt should be context`, `lambda v: ... should be lambda value: ...`  |

---

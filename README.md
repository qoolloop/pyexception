# About pyexception

Here is an implementation of an exception handling framework.
It is centered around the concepts explained in "Practical Exception Handling".
https://qoolloop.org/en-us/exception-handling

Please be aware that this is an experimental release and a proposal. Future versions may not be
compatible. Compatiblity issues may be avoided by using git hash codes.


# Comments from Claude 2025/7/8

What do you find novel about this library?

● Looking at this pyexception library, several novel aspects stand out:

  *Structured Exception Information*: The info dictionary approach is
  interesting - exceptions carry structured data specifically designed for
  UI display and debugging, rather than just error messages.

  *Unified Recovery Pattern*: The RecoveredException base class creates a
  single handler interface for all recoverable exceptions regardless of
  their underlying cause, which simplifies error handling architecture.

  *Context-Aware Assertions*: The fatal_section() and nonfatal_section()
  context managers that dynamically change assertion behavior based on
  program state is clever - assertions can be more or less strict depending
   on whether side effects have occurred.

  *Thread-Local Configuration*: Using thread-local storage for assertion
  configuration allows different execution contexts to have different error
   handling behaviors simultaneously.

  *Reason-Based Exception Design*: The Reason class hierarchy separates the
  "what happened" from the "why it matters" - exceptions can have detailed
  reasons with metadata while maintaining clean handler interfaces.

  *Assertion-Exception Integration*: The tight coupling between assertions
  (expect(), imperative()) and the exception framework, where assertions
  can be configured to log, warn, or raise based on context rather than
  being binary pass/fail.

---
title: "Run Command Examples"
category: REFERENCE
document_type: tutorial
difficulty: intermediate
time_estimate: 20-25 minutes
user_personas: ["script_developer", "advanced_user"]
operators: []
concepts: ["scripting", "delayed_execution", "asynchronous_operations"]
prerequisites: ["Python_fundamentals"]
workflows: ["managing_timed_events", "optimizing_performance", "advanced_scripting"]
keywords: ["run", "delay", "script", "asynchronous", "frame", "endframe", "kill"]
tags: ["python", "api", "core", "scripting", "timing"]
related_docs:
- MODULE_td
- CLASS_Run
---

# Run Command Examples

This page is also posted as a tutorial with an attached example file on the Derivative website here.

## Contents

- [The Run Command](#the-run-command)
- [Running A Simple Script](#running-a-simple-script)
- [Running A Script With A Delay](#running-a-script-with-a-delay)
- [Including Python Objects/Arguments In The Run Command](#including-python-objectsarguments-in-the-run-command)
- [Timing of Evaluation of Arguments Vs Script](#timing-of-evaluation-of-arguments-vs-script)
- [Using endFrame](#using-endframe)
- [The delayRef Argument](#the-delayref-argument)
- [Changing Context With fromOP](#changing-context-with-fromop)
- [Altering Context With asParameter](#altering-context-with-asparameter)
- [Advanced run Command Features](#advanced-run-command-features)
  - [Killing Run Objects](#killing-run-objects)
  - [The runs Collection](#the-runs-collection)
  - [Killing All Run Objects](#killing-all-run-objects)
  - [Killing Select Run Objects](#killing-select-run-objects)
  - [Testing Run Object Status](#testing-run-object-status)
- [Single Update Design Pattern Example](#single-update-design-pattern-example)

## The Run Command

The `run` command allows you to run a string as a Python statement. It has many a number of options available as to how to run the command. The most powerful feature of these options is to allow you to delay the execution for a certain number of frames or milliseconds. Below is the full wiki documentation for `run`. This tutorial will go through all the options one by one.

`run(script, arg1, arg2..., endFrame=False, fromOP=None, asParameter=False, group=None, delayFrames=0, delayMilliSeconds=0, delayRef=me)`→ `[CLASS_Run]`:

> Run the script, returning a `Run` object which can be used to optionally modify its execution. This is most often used to run a script with a delay, as specified in the `delayFrames` or `delayMilliSeconds` arguments.
>
> - `script` - A string that is the script code to execute.
> - `arg` - (Optional) One or more arguments to be passed into the script when it executes. They are accessible in the script using a tuple named `args`.
> - `endFrame` - (Keyword, Optional) If True, the execution will be delayed until the end of the current frame.
> - `fromOP` - (Keyword, Optional) Specifies an optional operator from which the execution will be run relative to.
> - `asParameter` - (Keyword, Optional) When `fromOP` used, run relative to a parameter of `fromOP`.
> - `group` - (Keyword, Optional) Can be used to specify a string label for the group of `Run` objects this belongs to. This label can then be used with the `td.runs` object to modify its execution.
> - `delayFrames` - (Keyword, Optional) The number of frames to wait before executing the script.
> - `delayMilliSeconds` - (Keyword, Optional) The number of milliseconds to wait before executing the script. This value is rounded to the nearest frame.
> - `delayRef` - (Keyword, Optional) Specifies an optional operator from which the delay time is derived. You can use your own independent time component or `op.TDResources`, a built-in independent time component.

## Running A Simple Script

At its most basic, `run` allows you to execute a string as a Python script. The following is exactly the same as if you had executed the script argument without wrapping it in the `run` command.

```python
run("print('hello, world')")
```

## Running A Script With A Delay

Delaying the script is as simple as adding a `delayFrames` or `delayMilliSeconds` argument.

```python
run("print('hello, world')", delayFrames=60)
run("print('hello, moon')", delayMilliSeconds=2000)
```

## Including Python Objects/Arguments In The Run Command

You can include any number of `args` that will be inserted into the command when it executes. This is useful for inserting variables and running other functions.

```python
location = 'world'

# our first argument is a string, then next is a variable
run('print(args[0] + ", " + args[1])', 'hello', location, delayFrames=60)

# running another function using args
def otherFunc(thing):
    print('yo,', thing)

run('args[0]("moon")', otherFunc, delayMilliSeconds=2000)
```

## Timing of Evaluation of Arguments Vs Script

The arguments passed to the `run` command are evaluated when the `run` command is started. Everything in the script itself is evaluated when the `run` command is executed.

```python
# Note that the first two delayed items use args to print the frame. These are calculated when the delay
# is started. The last two evaluate the frame in the run statement, so they are calculated when the run
# command actually executes.

print('Current Frame:', absTime.frame)
run("print('hello, world. Frame:', args[0])", absTime.frame, delayFrames=60)
run("print('hello, moon. Frame:', args[0])", absTime.frame, delayMilliSeconds=2000)
run("print('hello, Venus. Frame:', absTime.frame)", delayFrames=180)
run("print('hello, Mars. Frame:', absTime.frame)", delayMilliSeconds=4000)
```

## Using endFrame

The `endFrame` argument causes the script to be run at the end of the current frame. In the example below, both statements run in the same frame, but the `run` command happens second because it is deferred to frame end, while the `print` command happens immediately.

```python
run("print('hello, world. Frame:', absTime.frame)", endFrame=True)
print("hello, moon. Frame:", absTime.frame)
```

## The delayRef Argument

Using the `delayRef` argument, you can provide a component whose timeline will be used for the delay instead of the main TouchDesigner timeline. This can be your own independent time component but more commonly you can use `op.TDResources` which has independent time. Generally, this will be used for a delayed run that will still happen even if the TouchDesigner timeline is paused. If you don't use this argument, TD doesn't consider time to be passing for the delay unless the timeline is playing!

```python
# pause timeline before trying this
run("print('hello, world')", delayFrames=60)
run("print('hello, moon')", delayMilliSeconds=2000, delayRef=op.TDResources)
# unpause timeline after a couple seconds
```

## Changing Context With fromOP

The `fromOP` argument allows you to run the script as if it is being run from another operator. In general, this will only affect Python that is sensitive to its TouchDesigner network context, such as `me` and `op`.

```python
run('debug(me)')
run('debug(me)', fromOP=root)
```

## Altering Context With asParameter

The `asParameter` argument affects a legacy run behavior where, when `fromOP` is specified, `op` will search inside that operator. That is, if you had `torus1` inside `geo1`, `run("print(op("torus1"))', fromOP=op('geo1'))` would find the child of `geo1`, as opposed to searching for a sibling as one might expect. Setting this argument to `True` (the default is `False`) would make it search for the sibling instead. This argument is only relevant when `fromOP` is set to a COMP, and only affects the operation of the `op` object.

```python
run("print(op('torus1'))", fromOP=op('geo1'))
run("print(op('torus1'))", fromOP=op('geo1'), asParameter=True)
```

## Advanced run Command Features

The basic usage of `run` is covered above. This section will detail some more advanced run features including the `Run` object and the `runs` collection.

### Killing Run Objects

The `run` command returns a `Run` object which can be stored in a variable. This is most commonly used to cancel scheduled commands via the object's `kill` method.

```python
worldRun = run("print('hello, world')", delayFrames=60)
moonRun = run("print('hello, moon')", delayMilliSeconds=2000)

print(worldRun)
worldRun.kill()
```

### The runs Collection

All the active `Run` objects in your project can be accessed via the `runs` collection.

```python
run("print('hello, world')", delayFrames=60)
run("print('hello, moon')", delayMilliSeconds=2000)

print('total runs:', len(runs))
for i,r in enumerate(runs):
    print(i, r.remainingFrames)
```

### Killing All Run Objects

It's fairly simple to kill all active `Runs` by combining the techniques above...

```python
run("print('hello, world')", delayFrames=60)
run("print('hello, moon')", delayMilliSeconds=2000)

for r in runs:
    r.kill()    

run("print('goodbye, world')", delayFrames=60)
```

GOTCHA: Many internal and user-built TouchDesigner features use `run` to deal with timing. Killing all active runs can cause unexpected and hidden problems. It is much safer to kill only select run objects...

### Killing Select Run Objects

Killing only select run objects can be more complicated. To facilitate this, you can assign a `group` string when you create a `Run` to distinguish the objects from one another. The `group` is available as a member of the `Run`.

```python
run("print('hello, world')", group='world', delayFrames=60)
run("print('hello, moon')", group='moon', delayMilliSeconds=1000)
run("print('hello, Luna')", group='moon', delayMilliSeconds=1000)
run("print('hello, Earth')", group='world', delayMilliSeconds=1000)

for r in runs:
    if r.group == 'world':
        r.kill()
```

Alternatively, you can examine a run object's `source` member to determine if you want to kill it. This feature allows you to test the actual code string that will run. In the following example, the run with the word "Earth" is killed.

```python
run("print('hello, world')", group='world', delayFrames=60)
run("print('hello, moon')", group='moon', delayMilliSeconds=1000)
run("print('hello, Luna')", group='moon', delayMilliSeconds=1000)
run("print('hello, Earth')", group='world', delayMilliSeconds=1000)

for r in runs:
    if 'Earth' in r.source:
        r.kill()
```

### Testing Run Object Status

Run objects that have already executed will cause an exception if you try to access them. This creates a bit of a tricky scenario if you want to test one that is stored in a variable to see if it is still pending. To get around this conundrum, use a `try/except` clause testing for `tdError`.

```python
worldRun = run("print('hello, world')", delayFrames=60)
moonRun = run("print('hello, moon')")

try:
    if worldRun.active:
        print('world active')
except tdError:
    print('world inactive')

try:
    if moonRun.active:
        print('moon active')
except tdError:
    print('moon inactive')

print("nThis one is okay because it's active ---")
print(worldRun.active)
print("nThis one errors because it's not ---")
print(moonRun.active)
```

## Single Update Design Pattern Example

One very useful design pattern for `run` is when you need to do some kind of update operation that can be triggered by many different events, but you only want to do the actual update once per frame. The following example sets this up so that any event(s) can call the `scheduleUpdate` function multiple times per frame, and the actual `update` function will only run once at the end of that frame.

```python
# run the "update" function anywhere that requires an end of frame
# update. The update will only run once! 

scheduledUpdateRun = None

def update():
    # the actual update function
    print('Run updater!')
    global scheduledUpdateRun
    scheduledUpdateRun = None

def scheduleUpdate():
    # called to indicate an update is needed
    global scheduledUpdateRun

    print('Called schedule update!')
    if scheduledUpdateRun is None:
        scheduledUpdateRun = run('args[0]()', update, endFrame=True)

scheduleUpdate()
scheduleUpdate()
scheduleUpdate()
```

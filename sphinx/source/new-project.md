Guide for creating a new Seamless project
=========================================

**This is a beginner's guide. Important aspects are explained. Guidelines and a recipe are provided. Once you know what you are doing, adapt it to your needs.**

Only basic Seamless features (contexts, cells and transformers) are used. See the [basic example](http://sjdv1982.github.io/seamless/sphinx/html/introduction.html#basic-example) for a demonstration.

Contexts contain contexts, cells and transformers. The whole Seamless graph is a top-level context.

Cells contain data and code.

Transformers perform a data transformation (computation), with cells as input, and one cell as the output. A transformation can be in bash, docker, Python, or a compiled language.

## Project aspects

A Seamless project must address the following aspects:

- *Dependency graph*. Which data depends on which transformation? Which transformation depends on which data?

- *Topology*. The dependency graph annotated with names, formats, programming languages, and other details that are necessary to make its execution well-defined.

- *Code and parameters*. Together, these are the inputs that are not user-defined, i.e. their content must be specified.

- *Validation*. Detection of invalid input and output data.

- *Monitoring*. Execution status, progress, error messages.

- *User experience (UX)*. Web forms/widgets for the input. Visualization of the output.

- *Deployment*. Where will each transformation run? What are the resource limits? Where is the data stored, and for how long?

- *Configuration*. Make sure that validation, monitoring, user experience, and deployment can be customized by changing some settings.


Seamless is very flexible, in that you can completely change every aspect at any time, while everything keeps running. Still, it recommended to roughly divide the creation of a project into the following phases: design, implementation, visualization, validation, publishing.

## Project phases


## Design phase

First, a dependency graph is designed. This part must be done outside of Seamless, as Seamless does not (yet) support visual programming.

### Abstract dependency graph

You should start with thinking of dependencies in an abstract way. Think of your program as a set of processes with well-defined inputs and outputs. Draw some flowcharts.

Seamless is very strict about dependencies. Normal shell commands may implicitly assume that a certain package is installed, or that certain files are present. In contrast, Seamless transformations are executed in isolation: if there is any implicit dependency, they will loudly fail. This is considered a good thing.

### Concrete dependency graph

Once you have an abstract dependency graph, try to make it more concrete. Formulate every process as a transformation with one code input, several data/parameter inputs, and one data output. Decide the programming language for each transformation. Choose names for each input.

### Command line workflows

Dependency graphs are most straightforward if you are porting a workflow of command line tools, where all inputs and outputs are files. There several tools that specialize in such workflows, such as SnakeMake and NextFlow. You could define your concrete dependency graph using one of these tools, and then convert it to Seamless to add monitoring and visualization. For SnakeMake, there is an automatic converter (see [example](https://github.com/sjdv1982/seamless/tree/stable/examples/snakemake-tutorial)).

A transformation may wrap a single bash command that invokes a single command line tool, or a small block of commands. In Seamless, such a transformation will be either a bash transformer ([example](https://github.com/sjdv1982/seamless/blob/stable/tests/highlevel/bash.py)) or a Docker transformer ([example](https://github.com/sjdv1982/seamless/blob/stable/tests/highlevel/docker_.py)). In both cases, the transformer will have a code cell written in bash, and the result must be written to the file `RESULT`. For multiple outputs, create a tar file and copy that to `RESULT`. Within a bash/Docker transformer, every input X is available as file X. Small inputs are also accessible as a variable $X. After execution, all files are deleted.

There are two strategies to define a command-line transformation.

1. The best way is use a bash transformer and include the source code of every command line tool (except standard UNIX commands). This will make the transformation reproducible. The command line tool must not have any hard-coded "magic files" where it depends on. Also, if it is written in a compiled language, things become quite difficult. Seamless has compiled transformers, but they assume that data is exchanged as function arguments, and not via the file system.

2. The alternative is to treat a command line tool as part of the environment. In that case, use a Docker transformer, where the command line tool must be installed in the Docker container. This is appropriate if the command line tool is immutable over the course of the project. You may also be forced to go this route if the assumptions above are violated. Any magic files must be installed in the Docker container.

## Implementation phase

Here, the design is implemented in Seamless.

- The *topology* corresponds to the concrete dependency graph of the previous section. It is defined by modifying the Seamless graph. This is done from IPython and/or Jupyter, as shown in the [basic example](http://sjdv1982.github.io/seamless/sphinx/html/introduction.html#basic-example).

- *Code and parameters* are defined as cell checksums in the Seamless graph. However, during development it is common to link them to files, and let the files have priority over the graph in case of a conflict. The files should be under version control (Git).

- *Monitoring* is not part of the graph. In IPython/Jupyter, you can interactively access `Context.status` ,  `Cell.status` and `Transformer.status` , as well as `Cell.exception` and `Transformer.exception`. You can monitor this in the browser by setting up a poller that assigns the statuses to the cells of a second Seamless context (see the Recipe below).

In addition, you can get the stdout and stderr of a transformer using `Transformer.logs`.

### Debugging

To debug your code, you can use either print statements, or a debugging session with breakpoints.

#### Debugging with print statements

Seamless transformations can be executed anywhere. Therefore, they do not print their stdout or stderr to any terminal while they execute. Stdout and stderr are only captured when the transformation has finished.

For Python transformers, the transformation is aborted if an exception is raised. `Transformer.exception` will then contain the exception traceback, stdout and stderr.
If no exception is raised, stdout and stderr can be retrieved using `Transformer.logs`

For bash/Docker transformers, if any launched process returns with a non-zero error code, the transformation is aborted. `Transformer.exception` will then contain the bash error message, stdout and stderr. Else, stdout/stderr will be discarded. Therefore, if you want to debug with print statements, exit with a non-zero exit code (`exit 1`).

For compiled transformers (i.e. written in C/C++/Fortran/...), you should *not* do `exit(...)` with a non-zero exit code: this kills the transformation process immediately, including the machinery to capture stdout and stderr. Instead, make the main `int transform(...)` function return a non-zero value.

#### Debugging sessions

Visual Studio Code and other IDEs do not yet support Seamless transformers.

***Python transformers***

To debug a Python transformer, you can use a slightly modified version of the pdb debugger. Add the following to your transformation code:
```python
from seamless.pdb import set_trace
set_trace()
```

NOTE: unfortunately, the pdb debugger only works if you execute Seamless with `python`,
not with `ipython` or Jupyter.


***Compiled transformers***

Compiled transformers can be debugged with a debugger such as gdb.

For this, set `Transformer.debug` to `True` and re-translate the graph.
(You may have to make a minimal change in the source code or input. Remind that Seamless does not re-execute transformations that have already been performed,
debug or not).

Once the transformer executes, you will see a Process ID printed.

Start a separate shell in the same Docker container using `seamless-shell-existing`
You will be root in this shell.

Type "gdb" to start a GDB terminal.

In the GDB terminal, type the following (where XXX is the process ID):
```
(gdb) attach XXX
(gdb) break main.cpp:transform
(gdb) signal SIGUSR1
```
and gdb will break when your main `transform` function starts.

If your transformer is written in C, the main file will be "main.c" instead of "main.cpp".

Whenever the transformer re-executes (due to changed source code or inputs), you will have to re-attach, but your breakpoints normally remain active.

NOTE: integration with Visual Studio code is currently in progress.

## Visualization phase

### Using Jupyter notebooks ###

*User experience* (UX) can be done initially using Jupyter notebooks (very quick to set up). See [this simple example](https://github.com/sjdv1982/seamless/blob/stable/tests/highlevel/traitlets.ipynb), to be opened with `seamless-jupyter`.

### Using HTML/JS

More powerful is to use UX cells (HTML, JS, CSS). These cells are shared over HTTP (read-only), so that they can be accessed via the browser. Input cells (read-write) and output cells (read-only) are also shared over HTTP, so that the UX cells (loaded in the browser) can access and manipulate them. See [this example](https://github.com/sjdv1982/seamless/blob/stable/tests/highlevel/share-pdb.py), to be opened with `seamless-ipython -i`.

### Web page generator

As of Seamless 0.5, a Seamless project now automatically includes a web page generator.
When you share a cell (and retranslate the graph), an entry is automatically added in
`/web/webform.json` . These entries are used to generate the web page in `web/index.html` and `web/index.js`. The web page is available under `http://localhost:<REST server port>`, normally `http://localhost:5813`.

- Each entry in `/web/webform.json` describes the web component for the cell, and its parameters. All web components are in `/web/components/`. The "component" attribute of an entry can be the name of any component in that folder. See the README for each component for the required parameters (the "params" attribute of the entry).

- You can also modify or create new components in `/web/components/`, and the web page will be updated.

- You can manually edit `web/index.html` and `web/index.js`. Your modifications are automatically merged with the auto-generated HTML and JS. Sometimes, this can give rise to a merge conflict. Therefore, monitor and resolve `web/index-CONFLICT.html` and `web/index-CONFLICT.js`.

- Likewise, when a modified context leads to added or removed entries in `/web/webform.json`, and these are automatically merged with your modifications. Resolve `web/webform-CONFLICT.txt` in case of a conflict.

## Validation phase

As a rule, *validation* happens on the data. Transformation code is not the correct place to do validation.

Validation in Seamless is defined in schema cells. Schema cells contain a superset of JSON Schema. You can write them directly, but it is easier to fill them up using the `Cell.example` attribute. See [this example](https://github.com/sjdv1982/seamless/blob/stable/tests/highlevel/highlink-cpp.py), to be opened with `seamless-ipython -i`.

Validation errors show up in the monitoring. At this point, the monitoring (which had previously its own UX cells) should be adapted so that error messages and progress are displayed in the main web UI.

This is also the time to create tests. A unit test should be a small Seamless context linked to the same files as the main project for code and schema cells. Other tests can be a copy of the main graph with some parameters changed. *Make sure to create some tests that are designed to fail, to verify that a correct and comprehensible error message is reported*.

## Publishing phase

*TODO: expand this section*

Seamless deployment is done using Cloudless (https://github.com/sjdv1982/cloudless, WIP).

You will need the .seamless file, and a zip file generated with `ctx.save_zip(...)`.

For configuration, it is recommended to use YAML or CSON cells (*TODO: high-level test/example*)


Recipe for a new project
========================

*(There are lots of other ways how you can set things up: no Jupyter, no monitoring, no backups, Redis instead of zip files, ...  Still, below is a solid example. Just substitute PROJNAME with your project's name.)*

## A. Project creation

Seamless is well-suited for collaborative projects, where one person is the ***host*** and the others are ***guests***. The host must have Seamless installed, but the guests can be under Windows or any OS, as long as they can install Visual Studio Code.

Specific instructions are below.
Alternatively, for a solo project, do the obvious (install Seamless, create a new directory, `git init`) and go to section B.

### A1. Collaborative project creation
**Only the host needs to do this. If you are a guest, go to section C.**

1. Install [Visual Studio Code](https://code.visualstudio.com/).

2. Step 3-5 are for hosting on a remote machine (via ssh). If you are hosting from your own local machine, go to step 6.
   *It is not recommended to host a remote directory that has been mounted locally (sshfs).*

3. In Visual Studio Code, install the Remote Development extension (Ctrl+Shift+X, type "Remote Development").

4. Set up your `~/.ssh/config`.  Below is an example for a machine *gateway* that is accessible directly, and a machine
*workstation* that is only accessible from *gateway*:
```
Host gateway
    HostName 999.999.1.99
    User yourname

Host workstation
    HostName 192.168.1.86
    User yourname
    ProxyCommand ssh -q -W %h:%p gateway
```
To verify that it works, do `ssh workstation` and/or `ssh gateway` from the command line.

5. In Visual Studio Code, connect to the Remote Explorer (icon on the left, or Ctrl-Shift-P => type "Remote Explorer").
Connect to the remote host machine.

6. In Visual Studio Code, type `Ctrl-Shift-(backtick)` to open a new terminal, or use the Terminal menu. Create a new directory PROJDIR, go there. and do `git init`.

7. In Visual Studio Code, in the File menu, click "Add Folder to Workspace".
After adding the new directory, save the workspace as PROJDIR/PROJNAME, where PROJNAME is the name of the project.

## B. Project initialization

**For a collaborative project, only the host needs to do this (on the host machine). If you are a guest, go to section C.**

1. On the host machine, make sure you have the latest version of Seamless installed, using `docker pull rpbs/seamless` and `conda install -c rpbs seamless-cli`.

2. Create a new directory. Open a shell in the new directory.
Initialize git with `git init`

Type `seamless-new-project PROJNAME` where `PROJNAME` is the name you choose for your project.

## C. Project implementation

### C1. For collaborative project hosts

**For a collaborative project, only the host needs to do this. If you are a guest, go to section C2**

*(If this is a solo project, go to step 6)*

1. Connect to the host machine. If the project runs on a remote machine, connect to the remote workspace that you set up before, using the Remote Explorer (icon on the left, or Ctrl-Shift-P => type "Remote Explorer") in Visual Studio Code.

2. In Visual Studio Code, install the Live Share extension (Ctrl+Shift+X, type "Live Share").

3. Click on the "Live Share" text at the bottom of the screen and start a Live Share session.

4. At the top of the window, click on "Sign in with  GitHub". This will open a browser window, where you give permission. Follow the instructions.

5. At the bottom, instead of the "Live Share" text, there will now be your GitHub name (it should still be there the next time you start Visual Studio Code).
Click on it, then on "invite others", and paste the link in a message to the guests.

6. Open a new terminal (`Ctrl-Shift-(backtick)` in Visual Studio Code).
   The following steps explain how to open your project in Jupyter.
   If you prefer to use IPython instead, go to step 9.

   Type `seamless-jupyter-trusted`. Normally, this will print
   `The Jupyter Notebook is running at: http://localhost:8888/`
   But if port 8888 is already in use, it may be 8889 or a higher number instead.

   If you are hosting on a remote machine, you must share this port, as well as the Seamless HTTP ports (see step 9).

7. Open the Jupyter window in the browser. A notebook called PROJNAME.ipynb should already exist in `cwd`.

If not, go to `cwd` and start a new Python3 notebook. Rename it to PROJNAME. In the first cell, type:
    ```ipython
    %run -i init-project.py
    await load()
    ```
    and execute it.

8.  Open a second terminal and type `seamless-jupyter-connect` (pressing Tab for completion is recommended).
    This opens a console that connects to the same kernel as the Notebook. From here (or, if you really want, from the Notebook) you can modify `ctx` to implement the topology.

9. Instead of using Jupyter, you can open your project in IPython instead by typing
`seamless-load-project-trusted`.

10. Now you must decide now much you trust the guests.

- If you do nothing, they can only edit files. In the case of file-mounted code cells, this still means arbitrary execution of code.

- To let them see any web form, you must expose the HTTP ports used by Seamless, which are by default 5138 and 5813 (this is reported in the first Jupyter Notebook output).
In Visual Studio Code, click again on your name on the bottom and select "Share server" and enter the port number. Once you have shared both ports, you and any guest can see the monitoring at http://localhost:5813/status/status.html

- To let them help with the topology, you must share the terminal in which the "jupyter console" command is running. Terminals can be shared in the Live Share menu. Note that you can launch arbitrary commands from within a Jupyter console.

- If you want them to get full Jupyter Notebook access, you must share the Jupyter port (8888). However, Jupyter Notebooks do not really support collaborative editing, so communicate clearly. Note that Jupyter allows you to open bash shells in the browser.

11. Start the implementation stage. Modify the topology  in the console terminal (do `await ctx.translation()` after modification, and type `save()` often!). Mount cells to the file system, and tell the guests to edit them. Monitor error messages in the browser.
Then, proceed to the visualization and validation phases. You can start visualization in the Jupyter Notebook, then move on to HTML/JS. For validation, you can start with the `Cell.example` attribute, then mount the schemas to the file system for editing.

### C2. For collaborative project guests

1. Install [Visual Studio Code](https://code.visualstudio.com/). This can be the Linux, OSX or Windows version.

2. In Visual Studio Code, install the Live Share extension (Ctrl+Shift+X, type "Live Share").

3. Click on the "Live Share" text at the bottom of the screen and start a Live Share session.

4. At the top of the window, click on "Sign in with  GitHub". This will open a browser window, where you give permission. Follow the instructions.

5. At the bottom, instead of the "Live Share" text, there will now be your GitHub name (it should still be there the next time you start Visual Studio Code).
Click on it, then choose "Join Collaboration Session". Enter the link that the host has provided to you.

6. In the browser, open Jupyter (http://localhost:8888) and the monitoring page (http://localhost:5813/status/status.html). In Jupyter, click on "Running" and then on the notebook.

## D. Version control

*TODO: expand this section*
(Discuss `/vault` and .gitignore. The vault contains the value for each checksum in
the graph )
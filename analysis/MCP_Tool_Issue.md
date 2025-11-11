 Perfect! Now I have comprehensive information. Let me compile the research findings into a complete report.

       ---
       📊 Research Report: FastMCP Alternatives for MCP Server Implementation

       Based on my research, here's a comprehensive analysis of alternatives to FastMCP for building MCP servers, with a focus on reliability, stability, and
       production readiness.

       ---
       🔍 1. Available MCP Server Implementation Options

       Option A: Official MCP Python SDK - Low-Level Server ⭐ RECOMMENDED

       - Package: mcp (PyPI, v1.13.1+)
       - Repository: https://github.com/modelcontextprotocol/python-sdk
       - Import: from mcp.server.lowlevel import Server
       - Maintained by: Anthropic, PBC (official)

       Pros:
       - ✅ Official reference implementation (most stable, authoritative)
       - ✅ Full protocol control and customization
       - ✅ Direct access to lifecycle management (@server.list_tools(), @server.call_tool())
       - ✅ No abstraction bugs - you control all state management
       - ✅ Supports lifespan pattern with async context managers
       - ✅ Better suited for production when you need precise control
       - ✅ No dependency on FastMCP (fewer potential breaking changes)

       Cons:
       - ❌ More verbose - requires manual JSON schema definition
       - ❌ No automatic type inference from Python annotations
       - ❌ More boilerplate code for simple servers
       - ❌ Requires deeper understanding of MCP protocol
       - ❌ No decorator-based API (less Pythonic)

       Production Readiness: ✅ Production-ready - Official implementation, most reliable

       ---
       Option B: FastMCP 1.0 (Integrated into Official SDK)

       - Package: mcp (included in official SDK)
       - Import: from mcp.server.fastmcp import FastMCP
       - Status: Integrated into official SDK in 2024

       Pros:
       - ✅ Part of official SDK (maintained by Anthropic)
       - ✅ Simple decorator-based API (@mcp.tool(), @mcp.resource())
       - ✅ Automatic type validation from Python annotations
       - ✅ Good for prototyping and simple servers
       - ✅ Official support and maintenance

       Cons:
       - ❌ Less feature-rich than FastMCP 2.0
       - ❌ May have the same state management issues as FastMCP 2.0
       - ❌ Limited advanced features (no server composition, proxying, etc.)

       Production Readiness: ⚠️ Limited production features - Good for simple use cases

       ---
       Option C: FastMCP 2.0 (Standalone Project) ⚠️ CURRENT IMPLEMENTATION

       - Package: fastmcp (separate PyPI package, v2.12.2+)
       - Repository: https://github.com/jlowin/fastmcp
       - Import: from fastmcp import FastMCP
       - Status: Actively maintained, but separate from official SDK

       Pros:
       - ✅ Most feature-rich (server composition, proxying, OpenAPI/FastAPI generation)
       - ✅ Enhanced client capabilities and LLM sampling
       - ✅ Pluggable storage backends (Redis, encrypted disk)
       - ✅ Persistent authentication with OAuth support
       - ✅ Advanced MCP patterns and tool transformation
       - ✅ Backward compatible with v1.0

       Cons:
       - ❌ Known state management bugs (initialization, lifecycle issues)
       - ❌ Stateful SSE connections complicate horizontal scaling
       - ❌ In-memory session storage by default (single-pod limitation)
       - ❌ More abstraction = more potential for framework bugs
       - ❌ Separate project = potential divergence from official spec
       - ❌ Dependency licensing concern (Cyclopts v4 → docutils)

       Known Issues:
       1. Nested MCP servers lifespan issues (#139) - Servers get parent's context instead of their own
       2. FastAPI lifespan not respected (#580) - Generated servers don't honor FastAPI lifespan functions
       3. Multi-server client status bug (#1479) - is_connected() returns true if ANY server connected
       4. SSE initialization race condition (#423, #737) - "Received request before initialization was complete"
       5. OAuth token dropping (#9018) - Authentication lost after init failure

       Production Readiness: ⚠️ Requires additional engineering - Good for prototypes, needs hardening for production

       ---
       Option D: Official TypeScript/JavaScript SDK

       - Package: @modelcontextprotocol/sdk
       - Repository: https://github.com/modelcontextprotocol/typescript-sdk
       - Language: TypeScript/Node.js

       Pros:
       - ✅ Official implementation (Anthropic maintained)
       - ✅ Strong type safety with TypeScript
       - ✅ More mature than Python SDK (earlier release)
       - ✅ Good documentation and examples

       Cons:
       - ❌ Requires TypeScript/Node.js rewrite (not Python)
       - ❌ Major codebase migration effort
       - ❌ Loss of existing Python integrations

       Production Readiness: ✅ Production-ready - But requires complete rewrite

       ---
       🐛 2. Your Current Bug vs Alternatives

       Your Current Issue: _index_manager initialized with project_id=None because global state not set during indexing, only during search.

       Would this bug exist in alternatives?

       | Implementation | Bug Likely? | Reason                                                             |
       |----------------|-------------|--------------------------------------------------------------------|
       | Low-Level SDK  | ❌ NO        | You control state initialization explicitly - no hidden lifecycle  |
       | FastMCP 1.0    | ⚠️ MAYBE    | Same abstraction layer, similar lifecycle patterns                 |
       | FastMCP 2.0    | ✅ YES       | Same issue - framework manages lifecycle, state timing is implicit |
       | TypeScript SDK | ❌ NO        | Different implementation, but requires rewrite                     |

       Root Cause Analysis:
       - FastMCP's abstraction hides when global state is initialized
       - Tools can be called before _current_project is set
       - Low-level SDK forces you to manage state explicitly → harder to make this mistake

       ---
       📊 3. Production MCP Server Examples

       Official Reference Servers (TypeScript):
       - Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time
       - Framework: Low-level TypeScript SDK
       - Status: Educational examples, not battle-tested production systems

       Production Implementations:
       1. Qdrant MCP Server - Vector search integration
         - Uses class-based pattern: QdrantMCPServer (inheritable)
         - Production-ready vector database integration
         - Repository: https://github.com/qdrant/mcp-server-qdrant
       2. Microsoft MCP Servers - Azure, Microsoft 365, GitHub integrations
         - Repository: https://github.com/microsoft/mcp
         - Enterprise-grade implementations
       3. Community Awesome List - 100+ MCP servers
         - Repository: https://github.com/punkpeye/awesome-mcp-servers
         - Mix of production and prototype quality

       Key Observation: Most production servers use low-level SDK or framework-free approaches, not FastMCP.

       ---
       🎯 4. Migration Complexity Assessment

       Low-Level SDK Migration (RECOMMENDED)

       Effort: Medium (2-3 days)

       Changes Required:
       1. Replace @mcp.tool() decorators with manual tool registration
       2. Define JSON schemas explicitly (no auto-inference from types)
       3. Implement lifespan pattern with @asynccontextmanager
       4. Move global state to lifespan context (proper initialization)
       5. Update tool handlers to return dict/list instead of Pydantic models

       Example Before (FastMCP):
       @mcp.tool()
       async def search_code(query: str, k: int = 5) -> dict:
           """Search code with natural language query"""
           return {"results": [...]}

       Example After (Low-Level SDK):
       @server.list_tools()
       async def list_tools() -> list[types.Tool]:
           return [types.Tool(
               name="search_code",
               description="Search code with natural language query",
               inputSchema={
                   "type": "object",
                   "properties": {
                       "query": {"type": "string"},
                       "k": {"type": "integer", "default": 5}
                   },
                   "required": ["query"]
               }
           )]

       @server.call_tool()
       async def call_tool(name: str, arguments: dict) -> dict:
           if name == "search_code":
               return {"results": [...]}

       Benefits:
       - ✅ Explicit state management (no hidden bugs)
       - ✅ Full lifecycle control
       - ✅ Official implementation (most stable)
       - ✅ No framework abstraction bugs

       Risks:
       - ⚠️ More boilerplate (but predictable)
       - ⚠️ Requires deeper MCP protocol understanding

       ---
       FastMCP 1.0 Migration (Official SDK version)

       Effort: Low (< 1 day)

       Changes Required:
       1. Change import: from mcp.server.fastmcp import FastMCP
       2. Test for feature parity (may lack advanced FastMCP 2.0 features)
       3. Verify state management behavior

       Benefits:
       - ✅ Minimal code changes
       - ✅ Official SDK integration

       Risks:
       - ❌ May have same state management issues
       - ❌ Less feature-rich than FastMCP 2.0

       ---
       TypeScript SDK Migration

       Effort: Very High (2-3 weeks)

       Changes Required:
       1. Complete codebase rewrite in TypeScript
       2. Port Python-specific logic (AST parsing, tree-sitter, etc.)
       3. Retest all 43 tests

       Benefits:
       - ✅ Official TypeScript SDK (mature)
       - ✅ Strong type safety

       Risks:
       - ❌ Massive effort
       - ❌ Loss of Python ecosystem integrations

       ---
       🏆 5. Recommendation

       Best Option: Migrate to Official MCP Python SDK - Low-Level Server ⭐

       Why:
       1. Fixes your bug: Explicit state management prevents initialization timing issues
       2. Most stable: Official Anthropic implementation
       3. Production-ready: Full control, no abstraction bugs
       4. No framework lock-in: Direct protocol implementation
       5. Reasonable effort: 2-3 days vs weeks for TypeScript rewrite

       Migration Strategy:
       1. Phase 1: Implement lifespan pattern with proper state initialization
       2. Phase 2: Convert tool decorators to manual registration
       3. Phase 3: Define explicit JSON schemas for all tools
       4. Phase 4: Comprehensive testing (unit + integration)

       Expected Outcome:
       - ✅ project_id initialization bug eliminated (explicit lifespan context)
       - ✅ More reliable state management
       - ✅ Better production readiness
       - ✅ Easier debugging (no framework magic)

       ---
       Alternative: Fix Current FastMCP Implementation (Quickest)

       If migration is not feasible now, fix the current bug by:
       1. Using lifespan pattern to initialize _current_project on startup
       2. Adding explicit state validation before tool execution
       3. Defensive checks: raise clear errors if state not initialized

       Implementation:
       @asynccontextmanager
       async def app_lifespan(server: FastMCP):
           global _current_project
           # Initialize project from environment or config
           _current_project = os.getenv('CLAUDE_DEFAULT_PROJECT', None)
           yield
           # Cleanup on shutdown
           cleanup_resources()

       mcp = FastMCP('Code Search', lifespan=app_lifespan)

       Pros:
       - ✅ Quick fix (< 1 day)
       - ✅ No major refactoring

       Cons:
       - ❌ Doesn't address underlying framework limitations
       - ❌ Still vulnerable to other FastMCP bugs

       ---
       📝 6. Key Takeaways

       1. FastMCP 2.0 is NOT the most stable option - It's feature-rich but has known state management bugs
       2. Official low-level SDK is most reliable - Direct protocol control, no abstraction bugs
       3. Your bug is framework-specific - Caused by FastMCP's hidden lifecycle management
       4. Production servers avoid FastMCP - Most use low-level SDK or custom implementations
       5. Migration is worthwhile - 2-3 days effort eliminates entire class of bugs

       ---
       🔗 7. Additional Resources

       Official Documentation:
       - MCP Specification: https://modelcontextprotocol.io/specification/
       - Python SDK: https://github.com/modelcontextprotocol/python-sdk
       - Lifecycle Management: https://modelcontextprotocol.io/specification/basic/lifecycle

       Production Examples:
       - Qdrant MCP Server: https://github.com/qdrant/mcp-server-qdrant
       - Microsoft MCP Servers: https://github.com/microsoft/mcp
       - Community Servers: https://github.com/punkpeye/awesome-mcp-servers

       Known Issues:
       - FastMCP Issues: https://github.com/jlowin/fastmcp/issues
       - MCP Spec Discussions: https://github.com/modelcontextprotocol/modelcontextprotocol/discussions
       - SEP-1442 (Stateless MCP): https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1442

       ---
       ❓ Next Steps

       Would you like me to:
       1. Create a migration plan to low-level MCP SDK with detailed implementation steps?
       2. Implement a quick fix for the current project_id bug using lifespan pattern?
       3. Compare code complexity between FastMCP and low-level SDK side-by-side?
       4. Prototype a simple tool in low-level SDK to demonstrate the pattern?
</info>

- additionally study this article:
<info>
Advanced MCPs in Python: How Transitioning From FastMCP Wrappers Improved our FastAPI-MCP Tool
Miki Makhlevich
Miki Makhlevich

Follow
5 min read
·
Apr 10, 2025
363


1





Press enter or click to view image in full size

After only a month of maintaining FastAPI-MCP, my team faced a critical realization that would force us to throw away weeks of work: the “easy path” we’d chosen      
was leading to a dead end. Our journey of transforming FastAPI endpoints into Model Context Protocol (MCP) tools taught us a lesson about when to abandon 
convenient abstractions and dive into the technical depths that most developers try to avoid.

If you find this interesting, please visit FastAPI-MCP and give it a star. We have exciting new features on the roadmap and are also open to contributions!

The Initial Approach: Using FastMCP
The journey began with clear intentions. When 
Shahar Abramov
 started building FastAPI-MCP alongside 
Shira Ayal
, the path seemed clear: use FastMCP (the high-level wrapper) and parse the OpenAPI schema generated by FastAPI. This approach allowed fast implementation which      
enabled us to gain immediate attention from users, and appeared elegant on paper — FastAPI already provides detailed schema information about each endpoint, and      
FastMCP was extremely intuitive to use.

The implementation was straightforward. We’d:

Extract the OpenAPI schema from the FastAPI application
Parse the routes, parameters, and response types
For each route, generate corresponding MCP tools via FastMCP
Expose them through a server
This worked for basic use cases, but problems quickly emerged as users adopted the library for more complex scenarios.

Where Things Went Wrong
The first major issue appeared when handling input arguments. The functions were created statically rather than dynamically, which prevented proper parameter         
passing. This limitation became apparent when users attempted to use request bodies in their endpoints, resulting in server exceptions that made the tools 
effectively unusable for complex data scenarios. We didn’t notice this issue when publishing the library because our testing had focused solely on simple FastAPI     
examples, failing to account for more complex real-world implementations.

Our first attempt at a fix involved some creative metaprogramming, but the code quickly became convoluted and difficult to maintain. The approach required parsing    
 the OpenAPI schema to determine the arguments each tool needed, then dynamically generating functions to serve as the foundation for these tools. The resulting      
code looked something like this:

params = _get_params_from_openapi_schema(openapi_schema)
params_str = ", ".join(params.values())
kwargs_str = ', '.join([f"'{k}': {k}" for k in params])

dynamic_function_body = f"""async def dynamic_function({params_str}):
    kwargs = {{{kwargs_str}}}
    return await function_template(**kwargs)
"""
exec(dynamic_function_body)
We immediately recognized this as unreadable, nearly impossible to debug, and simply a bad practice. Worse yet, each new edge case required additional patches,       
creating an increasingly fragile codebase.

Meanwhile, users began requesting crucial features that were technically possible but increasingly difficult to implement with our existing architecture:

Selectively exposing only certain endpoints — required convoluted filtering logic on top of our OpenAPI schema parser
Custom authentication flows — demanded more wrappers on top of FastMCP's structure
Better error handling — needed intricate error propagation through multiple layers of abstraction
Support for more complex FastAPI configurations — forced us to add special case handling for complex input arguments
With each new feature request, our codebase grew more entangled. Easy features required disproportionate effort, and the convoluted structure deterred new 
contributors. Even we struggled to navigate the maze of special cases we’d created.

The Refactor Decision
Almost immediately after merging this patch, we knew we had to find a better solution — one that would work with the architecture instead of fighting against it.     
We needed to reconsider our original decision, as the higher-level abstraction that initially seemed helpful was now constraining what the library could do.

While this meant “throwing away” significant work, the library was still relatively slim, and we recognized it would be better to make this change early rather       
than regret it later when the codebase grew larger and more complex.

Going Low-Level: Embracing the MCP SDK Core
The refactored approach abandoned FastMCP entirely in favor of working directly with the low-level MCP SDK. This meant more code to write by giving up on this        
easy-to-use library, but it provided significantly more control over how tools were created and registered.

We created a new FastApiMCP class for laying the ground for extension and composability, separating the MCP instance creation and mounting. The new code looks        
roughly like this (and I encourage you to look at the full code in the open-source library here):

from mcp.server.lowlevel.server import Server
from mcp.types import Tool

from fastapi_mcp.openapi.convert import convert_openapi_to_mcp_tools


Class FastApiMCP:
    def __init__(
        self,
        # Input arguments
    ):
        self.operation_map: Dict[str, Dict[str, Any]]
        self.tools: List[Tool]
        # ... Additional configurations ...
        self.server = self.create_server()

    def create_server(self) -> Server:
        openapi_schema = get_openapi(...)
        self.tools, self.operation_map = convert_openapi_to_mcp_tools()
        
        # ... Additional logic, including defining handlers for call/list tools...
        @mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return self.tools
        # ... 
        
        mcp_server: Server = Server(
            # Server parameters
        )
        return mcp_server
By working at this level, we gained several advantages:

Complete control over tool generation
Fine-grained endpoint selection
Flexible routing options for placing the MCP server on any FastAPI app or API router
Ability to deploy MCP server separately from the API service
But while gaining those important abilities, we lost the ability to create extra tools using the @mcp.tool() decorator, as it was inherent to FastMCP. We know we     
will need to address this in the future.

The Results: Stability and Flexibility
The refactored codebase is not only more stable but also more flexible. Users can now:

Precisely control which endpoints are exposed as MCP tools
Handle complex parameter types correctly
Easily contribute to the open-source with their desired additions
The code is also more maintainable because it follows FastAPI’s internal patterns rather than trying to reinterpret them through an additional layer of 
abstraction.

Lessons Learned
This experience reinforced some valuable lessons about library design:

Higher-level abstractions come with trade-offs: While they can simplify common cases, they often make edge cases more difficult to handle.
Understand the tools you’re wrapping: FastMCP was designed for a different use case than what we needed. It allowed us to move fast in this constantly changing       
world, but also limited us, and we should have recognized this sooner.
Listen to user feedback: The requests for features were early signals that the architecture needed reconsideration.
Don’t be afraid to refactor: Sometimes the best way forward is to step back and reconsider fundamental assumptions.
The Path Forward
With a more solid foundation in place, FastAPI-MCP is now better positioned to evolve with user needs. The refactored architecture opens possibilities for new        
features while maintaining the simple developer experience that was the original goal.

If you’re building tools in the MCP ecosystem, we’d love to hear about your experiences and what features would be most valuable to you. The project is 
open-source, and contributions are always welcome!

Written in collaboration with 
Shira Ayal
 and 
Shahar Abramov
.
</info>

- additionally consider this official claude-agent-sdk-python repo:
https://github.com/anthropics/claude-agent-sdk-python

I want you to carefully analyze the information on issue and possible solutions and provide me with the reasoning for the most reliable solution 
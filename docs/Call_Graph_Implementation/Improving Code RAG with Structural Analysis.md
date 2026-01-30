# **Advancing Code Intelligence: A Comprehensive Analysis of Structural Tracing and Graph-Based Retrieval Augmented Generation**

## **Executive Summary**

The capability of Large Language Models (LLMs) to generate and understand software code has fundamentally transformed the discipline of software engineering. However, as these models move from generating isolated functions to reasoning about repository-scale architectures, a critical bottleneck has emerged: the limitations of "flat" Retrieval-Augmented Generation (RAG). Traditional RAG systems, which treat code as unstructured text, chunking it by arbitrary token counts and retrieving it via semantic similarity, fundamentally misunderstand the nature of software. Code is not merely text; it is a rigid, hyper-connected topology of logical dependencies, execution flows, and hierarchical structures. The fracture of these structures during standard retrieval leads to critical failures, including hallucinations of non-existent APIs, loss of variable scope, and the inability to resolve complex cross-file dependencies.1

This report provides an exhaustive examination of the recent methodological shifts toward **Structure-Aware Code RAG**. We analyze the transition from line-based indexing to sophisticated graph-based representations that trace the intrinsic structure of codebases. Central to this evolution are innovations such as **RepoGraph**, **Structural-Semantic Code Graphs (SSCG)**, and the **GRACE** framework, which leverage Abstract Syntax Trees (ASTs), Control Flow Graphs (CFGs), and Program Dependence Graphs (PDGs) to construct precise, traversable indices of software repositories.3

We explore the detailed mechanisms of **Ego-Graph retrieval**, **recursive summarization**, and **graph fusion**, which allow systems to retrieve not just semantically similar code, but functionally necessary dependencies. The analysis extends to the infrastructure enabling these advances—specifically the integration of **LlamaIndex**, **LangChain**, and graph databases like **Neo4j** and **Memgraph**—and evaluates their efficacy through rigorous benchmarks like **SWE-bench** and **RepoEval**. Our findings indicate that structural tracing and graph-based retrieval are no longer optional enhancements but are prerequisite architectures for the next generation of autonomous software engineering agents, delivering double-digit percentage improvements in issue resolution rates and retrieval precision.3

## **1\. The Crisis of Context in Repository-Scale Code Intelligence**

The software engineering domain faces a unique challenge in the application of Generative AI: the "Context Crisis." While LLMs have demonstrated remarkable proficiency in generating code within a limited context window (e.g., writing a single Python function), their performance degrades precipitously when tasked with modifying or reasoning about large, interconnected repositories. This degradation is not a failure of the model's reasoning capabilities per se, but a failure of the retrieval mechanisms that feed the model.

### **1.1 The Deterministic Nature of Code vs. Probabilistic Retrieval**

The core conflict arises from the mismatch between the deterministic nature of code and the probabilistic nature of standard retrieval systems. In natural language processing, "close enough" is often acceptable; retrieving a document about "canine behavior" is sufficient for a query about "dog training." In software, "close enough" is a syntax error. If a model generates a call to User.login() but fails to import the User class or relies on a deprecated method signature because the retrieval system fetched an outdated or irrelevant file, the generated code is functionally useless.

Standard RAG pipelines rely on "chunking"—splitting documents into fixed-size segments (e.g., 512 tokens). When applied to code, this heuristic is destructive. It blindly severs semantic units, separating function signatures from their bodies, or classes from their import statements. Recent research highlights that these "line-based" heuristics break the semantic structure of code, leading to a loss of critical context regarding return values, variable definitions, and scoping rules.1 For instance, if a function calculate\_tax() is split across two chunks, the LLM might retrieve the body of the calculation but miss the input parameters defined in the signature, leading to hallucinations about variable names.

### **1.2 The Dependency Blindness of Vector Search**

Furthermore, vector-based semantic search suffers from "dependency blindness." Embedding models like text-embedding-3 or CodeBERT optimize for semantic similarity—clustering code that *does* similar things. However, software logic is driven by *dependencies*, not just similarity. A high-level controller function process\_payment() is semantically distinct from the low-level database driver db.connect(), yet the former strictly requires the latter to function. A semantic vector search for "payment processing" will likely retrieve the controller and perhaps the payment interface, but it will almost certainly miss the database connection utility or the specific error-handling class defined in a separate utils module. Without these dependencies, the LLM cannot generate executable code that integrates correctly with the existing system.7

### **1.3 The Emergence of Structural Intelligence**

To resolve these issues, the field is moving toward **Structural Intelligence**. This paradigm treats a codebase not as a collection of text files, but as a **Knowledge Graph** where nodes represent code entities (functions, classes, modules) and edges represent rigorous logical relationships (calls, imports, inherits, instantiates). By tracing these structures effectively, RAG systems can transition from "guessing" context based on keyword similarity to "resolving" context based on the actual compiler-level topology of the application.9 This shift enables the construction of retrieval pipelines that respect the manifold of code execution, ensuring that if a function is retrieved, its necessary dependencies are retrieved alongside it.

## **2\. Theoretical Foundations: Mapping the Topology of Code**

Before analyzing specific tools and frameworks, it is essential to understand the theoretical models used to represent code structure. These models form the "physics" of the code graph universe, defining the entities that exist and the forces (relationships) that bind them.

### **2.1 The Abstract Syntax Tree (AST)**

The Abstract Syntax Tree is the most fundamental representation of source code structure. It is a tree representation of the abstract syntactic structure of source code written in a programming language. Each node of the tree denotes a construct occurring in the source code.

* **Role in RAG:** The AST provides the "ground truth" for chunking. Instead of splitting text at the 512th token, an AST-aware splitter traverses the tree to identify complete subtrees—such as a full function definition or a complete class declaration. This ensures that every "chunk" in the database is a syntactically valid and semantically complete unit.1  
* **Granularity:** ASTs allow for multi-level granularity. A RAG system can choose to index at the Class level, the Method level, or even the Statement level, depending on the desired precision of the retrieval.5

### **2.2 The Control Flow Graph (CFG)**

While the AST represents structure, the Control Flow Graph represents *execution*. It is a directed graph where nodes represent basic blocks (sequences of straight-line code without any jumps) and edges represent control flow paths (jumps, branches).

* **Role in RAG:** CFGs are critical for reasoning about logic and coverage. A RAG system augmented with CFG data can answer questions like "What are the possible execution paths that lead to this error state?" or "Which functions invoke this module under specific conditions?".12 This is vital for tasks like test generation and vulnerability analysis.

### **2.3 The Program Dependence Graph (PDG)**

The Program Dependence Graph combines control dependencies (from the CFG) with data dependencies. A data dependency exists between two statements if one statement defines a variable that the other statement uses.

* **Role in RAG:** PDGs unlock the ability to trace data flow. If a user asks, "Where is the user password sanitized?", a PDG-aware system can trace the variable holding the password from its input source through all transformations to identify the sanitization function (or the lack thereof).7 This level of insight is impossible with text-based retrieval.

### **2.4 The Structural-Semantic Code Graph (SSCG)**

The Structural-Semantic Code Graph is a high-level abstraction that synthesizes the AST, CFG, and PDG with semantic embeddings. It is a heterogeneous graph that explicitly models the "business logic" of the repository alongside its syntax.

* **Semantic Edges:** Unlike pure compiler graphs, SSCGs include edges based on semantic similarity. If two functions in different modules implement similar algorithms (e.g., two different sorting implementations), the SSCG connects them with a Semantically\_Similar edge. This allows the RAG system to identify code duplication and suggest refactoring opportunities.5

## **3\. Structural Parsing and Graph Construction Methodologies**

The construction of these graphs is a complex process involving static analysis, parsing, and sophisticated indexing. Recent methodologies have standardized around several key approaches for transforming raw code into queryable graph structures.

### **3.1 RepoGraph: Line-Level Dependency Mapping**

**RepoGraph**, introduced in late 2024, represents a significant leap in graph construction granularization. Unlike previous approaches that operated at the file or function level, RepoGraph constructs a graph where the fundamental nodes can be individual lines of code, specifically focusing on "Definition" and "Reference" relationships.3

#### **3.1.1 The Construction Algorithm**

The RepoGraph construction process is a multi-stage pipeline:

1. **Repository Traversal:** The system scans the repository, filtering for relevant code files (e.g., .py, .js, .java) while ignoring configuration or binary files.  
2. **Tree-sitter Parsing:** It utilizes **Tree-sitter**, a high-performance incremental parsing library, to generate ASTs for each file. Tree-sitter is chosen for its speed and robustness against syntax errors in incomplete code.3  
3. **Node Identification:** The parser identifies two primary types of nodes:  
   * **Definition Nodes (def):** These correspond to the explicit declaration of entities—classes, functions, methods, and global variables.  
   * **Reference Nodes (ref):** These correspond to the usage of these entities.  
4. **Edge Extraction:** The system traces specific edges:  
   * **E\_contain:** Captures the hierarchy (e.g., File A contains Class B).  
   * **E\_invoke:** Captures the call graph (e.g., Method X invokes Function Y).  
   * **E\_import:** Explicitly models file-to-file dependencies.  
5. **Graph Compilation:** These nodes and edges are compiled into a directed graph (often using NetworkX or a dedicated graph database).3

This fine-grained structure allows RepoGraph to answer highly specific queries. If a developer asks about a bug in line 42 of utils.py, the system can instantly retrieve the specific definition node for that line and traverse outward to find every other place in the codebase that references it, providing a complete "blast radius" for the bug.3

### **3.2 The GRACE Framework: Hierarchical Fusion**

The **GRACE** (Graph-Guided Repository-Aware Code Completion) framework introduces a hierarchical approach to graph construction, designed to manage the complexity of large repositories by stratifying the graph into abstraction levels.4

#### **3.2.1 Multi-Level Graph Hierarchy**

GRACE constructs three distinct but interconnected layers:

1. **Repository Layer:** This high-level view captures the file system structure (directories, files) and the import dependencies. It serves as the "map" for the RAG system to navigate the project's architecture.  
2. **Module Layer:** This layer models the relationships between classes and functions, including inheritance (extends, implements) and cross-function calls. It provides the "architectural" context.  
3. **Function Layer:** This is the most granular layer, capturing intra-function logic, including local variable data flow and control structures (loops, conditionals). It provides the "execution" context.

#### **3.2.2 Dynamic Graph Fusion**

A unique innovation of GRACE is **Graph Fusion**. When a user provides a query (e.g., an incomplete code snippet they are working on), GRACE parses this snippet into a temporary "Query Graph." It then fuses this Query Graph with the static Repository Graph.

* **Mechanism:** The system identifies anchor points—variable names or function calls in the user's snippet that match nodes in the repository graph.  
* **Benefit:** This allows the RAG system to "understand" how the user's new, uncommitted code interacts with the existing codebase. It can validate that the user is calling a function correctly according to its definition in the repository, or suggest method completions that are valid within the current scope.4

### **3.3 Code Property Graphs (CPG) for Security Analysis**

For security-focused RAG, **Code Property Graphs** offer a specialized construction methodology. CPGs are built by superimposing the AST, CFG, and PDG into a single multi-graph.

* **Construction Tooling:** Tools like **Joern** or **Ocular** are often used to generate CPGs. They parse the code and produce a graph where a single node (e.g., a variable assignment) might have edges from the AST (its syntactic parent), the CFG (the next statement to execute), and the PDG (the statement that uses this variable).7  
* **RAG Integration:** In a RAG context, this allows for complex "Taint Analysis" queries. An LLM can be prompted to "Find all paths where user input from HttpServletRequest reaches executeQuery without passing through a sanitizer." The RAG system traverses the PDG edges of the CPG to trace the data flow and confirm or deny the vulnerability.7

## **4\. Advanced Chunking Strategies for Code**

Once the structure is understood, the code must be divided into retrievable units. The naive approach of "chunking by token count" is being replaced by structure-aware strategies that preserve semantic integrity.

### **4.1 cAST: Chunking via Abstract Syntax Trees**

The **cAST** method utilizes the AST to create "Semantic Chunks."

* **Recursive Decomposition:** The algorithm starts at the root of the file's AST and recursively visits nodes.  
* **Size Heuristics:** For each node (e.g., a Class), it checks if the node fits within the target token window (e.g., 1024 tokens).  
  * If it fits, the entire subtree is preserved as a single chunk.  
  * If it is too large, the algorithm descends to the children (e.g., the Methods within the Class) and attempts to chunk them individually.  
* **Sibling Merging:** Crucially, if a node is too small (e.g., a one-line getter method), cAST merges it with its siblings. This prevents the database from being cluttered with millions of tiny, context-less fragments. The result is a set of chunks where each chunk is a meaningful, self-contained unit of logic.1

### **4.2 Hierarchy-Aware and Hybrid Chunking**

Beyond strict AST chunking, **Hierarchy-Aware Chunking** explicitly includes context from the parent structure in each chunk.

* **Context Injection:** When chunking a method, the system injects the class name and module documentation into the chunk's metadata or text. For example, a chunk for the run() method would be stored as:  
  Python  
  \# Context: Module: engine.py, Class: SimulationEngine  
  def run(self):  
     ...

  This ensures that even if the method body is generic, the retrieval system knows exactly which class it belongs to.17

**Hybrid Chunking** combines different strategies for different file types. It might use AST chunking for Python/Java files, Markdown-header chunking for documentation, and simple token chunking for plain text configuration files. This adaptive strategy ensures optimal retrieval across heterogeneous repositories.17

## **5\. The GraphRAG Architecture: Indexing and Storage**

Constructing the graph is a preprocessing step; utilizing it requires a robust architecture for indexing and storage.

### **5.1 Graph Database Integration (Neo4j, Memgraph)**

The industry standard for storing these complex structures is the Property Graph Database. **Neo4j** and **Memgraph** are dominant players, offering native support for the node-edge model required by Code RAG.

* **Schema Design:** The schema typically involves nodes labeled :File, :Class, :Function, and :Variable. Edges are typed as , , \`\`.  
* **Hybrid Indexing:** These databases support "Hybrid Indexing," where nodes effectively have two indices:  
  1. **Vector Index:** The embedding of the code source (generated by models like OpenAI or HuggingFace) is stored as a node property. This allows for semantic similarity search.  
  2. **Graph Index:** The relationships are indexed for rapid traversal. This allows for structural queries.5

### **5.2 JSON-Based Interchange Formats**

For lighter-weight applications or agent-based interactions, JSON is often used as the interchange format. The **JSON Graph Format (JGF)** or proprietary JSON schemas allow agents to pass graph structures (nodes and edges) as part of their context window or tool outputs.

* **Example Schema:**  
  JSON  
  {  
    "nodes": \[  
      {"id": "func\_a", "label": "process\_data", "type": "function", "file": "main.py"},  
      {"id": "func\_b", "label": "load\_config", "type": "function", "file": "utils.py"}  
    \],  
    "edges": \[  
      {"source": "func\_a", "target": "func\_b", "relation": "calls"}  
    \]  
  }

  This allows LLMs to "read" the graph structure directly without needing to query a database if the subgraph is small enough.21

## **6\. Retrieval Algorithms and Traversal Strategies**

The defining characteristic of GraphRAG is its retrieval logic. It does not simply "fetch top-k chunks"; it "traverses" the knowledge graph to reconstruct context.

### **6.1 Ego-Graph Retrieval**

**Ego-Graph Retrieval** is the primary mechanism used by frameworks like RepoGraph.

* **Algorithm:**  
  1. **Identify Anchor:** The system uses vector search or keyword matching to find the "Anchor Node" in the graph that matches the user's query (e.g., the separability\_matrix function).  
  2. **K-Hop Expansion:** It expands outward from the anchor to include all nodes within ![][image1] hops (edges). A 1-hop expansion includes all functions called by the anchor and all functions that call the anchor. A 2-hop expansion goes further, capturing the "neighbors of neighbors."  
  3. **Context Assembly:** The retrieved subgraph is "flattened" into a linear sequence of code blocks. Topological sorting is often applied to ensure that dependencies (definitions) appear before their usage (references) in the final prompt, mirroring the logical flow required by a compiler.3

### **6.2 Recursive Retrieval and Summarization**

**Recursive Retrieval** is designed to handle queries at varying levels of abstraction.

* **Summary Indexing:** The system generates natural language summaries for every node (e.g., "This class handles user authentication"). These summaries are embedded and indexed.  
* **Retrieval Process:**  
  1. **High-Level Scan:** The query is first matched against the *summaries*. This is computationally cheap and allows the system to identify relevant modules across the entire repository.  
  2. **Drill-Down:** Once a relevant summary is found (e.g., the Auth Module), the system retrieves the *links* to the underlying code chunks.  
  3. **Recursive Fetch:** The system then fetches the actual code associated with those modules. This "Zoom-In" approach allows for answering high-level architectural questions ("How does the system handle auth?") without hitting token limits.24

### **6.3 Graph Fusion and Dual-Path Encoding**

The **GRACE** framework utilizes a sophisticated **Dual-Path Encoding** strategy.

* **Parallel Retrieval:** The system executes two parallel searches:  
  * **Semantic Path:** Uses dense vector embeddings to find code that is textually similar to the query.  
  * **Structural Path:** Uses graph traversal to find code that is structurally related (dependencies, callers).  
* **Fusion:** The results are merged. If the semantic search finds a function foo(), and the structural search finds that foo() is heavily dependent on bar(), both are included in the final context.  
* **Graph-Aware Reranking:** The candidates are reranked using a scoring function that combines their semantic similarity score with a "centrality" score (e.g., PageRank), ensuring that critical utility functions are prioritized over obscure or dead code.4

### **6.4 Community Detection for Global Understanding**

Microsoft's **GraphRAG** introduces the use of **Community Detection** algorithms (like Leiden or Louvain) to organize the graph.

* **Mechanism:** The graph is partitioned into dense clusters or "communities" of nodes. In a codebase, these communities naturally correspond to functional subsystems (e.g., the UI layer, the Database layer, the API layer).  
* **Summarization:** The system generates a summary for each community.  
* **Global Querying:** When a user asks a broad question ("Describe the overall architecture"), the system synthesizes the answer from these community summaries rather than individual code files. This enables "Global Code Understanding," a capability that standard RAG lacks entirely.27

## **7\. Infrastructure and Tooling Ecosystem**

The implementation of these theoretical concepts is supported by a rapidly maturing ecosystem of tools.

### **7.1 LlamaIndex: Structural Parsing and Navigation**

**LlamaIndex** has become a cornerstone for structural RAG implementation.

* **CodeHierarchyNodeParser:** This specialized parser splits code into a hierarchy of nodes. Crucially, it creates a "skeleton" of the code structure. When a parent node (like a Class) is retrieved, it contains references (Node IDs) to its children (Methods) rather than their full text. This allows the LLM to see the "shape" of the class and request specific methods only if needed, mimicking a developer expanding code blocks in an IDE.29  
* **Property Graph Index:** LlamaIndex allows users to define custom extraction logic to populate a property graph, seamlessly integrating with vector stores for hybrid retrieval.31

### **7.2 LangChain: Orchestration and Tracing**

**LangChain** provides the orchestration layer for these complex flows.

* **GraphRetriever:** A specialized retriever class that enables graph traversal logic to be chained with standard LLM prompts.  
* **LangSmith Tracing:** For debugging, LangSmith allows developers to visualize the recursive retrieval steps. One can see exactly which summaries were hit, which nodes were expanded, and where the traversal might have failed (e.g., a missing import link). This "observability" is critical for tuning graph RAG pipelines.32

### **7.3 RDF and Ontology Standards**

For enterprise environments requiring strict data governance and interoperability, **RDF (Resource Description Framework)** is used.

* **Ontologies:** Organizations define formal ontologies (schemas) for their code assets using OWL. This allows for inference—an RDF reasoner can deduce relationships that aren't explicitly stated in the code (e.g., inferring that a module is "Deprecated" because it depends on a deprecated library).  
* **SPARQL:** These systems utilize SPARQL for precise structural queries (e.g., "Select all Classes where security\_level is 'Critical' and test\_coverage is \< 80%").34

## **8\. Benchmarking and Performance Analysis**

The adoption of structural RAG is driven by measurable performance gains on industry-standard benchmarks.

### **8.1 SWE-bench: The Gold Standard**

**SWE-bench** evaluates an AI's ability to solve real-world GitHub issues (bugs and features). It is the most rigorous test of repository-level engineering capability.

* **RepoGraph Performance:** Integrating RepoGraph into the **Agentless** framework resulted in a **29.67%** resolution rate on SWE-bench Lite, a massive improvement over the **2.67%** baseline of standard RAG. This represents a relative improvement of over **32%** across different models. The graph structure allows the agent to effectively "prune" the search space, focusing only on the relevant dependency subgraph rather than flailing through unrelated files.3

### **8.2 RepoEval: Retrieval Precision**

**RepoEval** measures the precision and recall of the retrieval step itself.

* **Impact of cAST:** The AST-based chunking method (cAST) improved **Recall@5** by **4.3 points** compared to line-based chunking. This metric indicates that the correct code snippet appeared in the top 5 results significantly more often. Furthermore, it boosted **Pass@1** (the probability that the generated code works on the first try) by **2.67 points**.1

### **8.3 CodeRAG-Bench: Holistic Evaluation**

**CodeRAG-Bench** provides a comprehensive evaluation across diverse tasks.

* **Graph vs. Dense:** The benchmark results highlight that graph-based retrievers significantly outperform dense-only retrievers on "multi-hop" queries—tasks that require reasoning across multiple connected files. Dense retrievers often fail to retrieve the "second hop" (the dependency of the dependency), whereas graph traversals capture this naturally.36

### **8.4 Table: Comparative Performance Metrics**

| Benchmark | Metric | Standard RAG (Line-Based) | Structure-Aware RAG (Graph/AST) | Improvement |
| :---- | :---- | :---- | :---- | :---- |
| **SWE-bench Lite** | Resolution Rate | 2.67% | 29.67% (RepoGraph) | **\+27.0% (Absolute)** |
| **RepoEval** | Recall@5 | 65.5% | 69.8% (cAST) | **\+4.3 Points** |
| **RepoEval** | Pass@1 | 49.03% | 51.7% (cAST) | **\+2.67 Points** |
| **Internal Ent. Data** | Precision@5 | 75% | 90% (Graph Framework) | **\+15%** 38 |

## **9\. Challenges, Limitations, and Future Outlook**

While Structure-Aware RAG offers substantial benefits, it is not without challenges.

### **9.1 The "Stale Graph" Problem**

Software repositories are dynamic; a single commit can alter the dependency structure, rendering the graph index obsolete.

* **Challenge:** Rebuilding the entire graph (parsing ASTs, calculating PageRank) for every commit is computationally prohibitive for large repositories.  
* **Solution:** Systems are moving toward **Incremental Indexing**, where only the changed files and their immediate neighbors are re-parsed and patched into the existing graph structure.39

### **9.2 The Polyglot Barrier**

Most graph construction tools (like RepoGraph) rely on language-specific parsers.

* **Challenge:** Creating a unified graph for a polyglot repository (e.g., a React frontend with a Python backend and Terraform infrastructure) is difficult. Tracing a "call" from a JavaScript fetch request to a Python API endpoint requires a "cross-language" edge that standard parsers cannot automatically detect.  
* **Future:** Future research is focused on **Neural Link Prediction**, using LLMs to infer these cross-language edges based on semantic similarity of API routes and variable names, effectively "stitching" the disparate graphs together.14

### **9.3 Agentic Graph Navigation**

The next frontier is **Agentic Navigation**. Instead of a single retrieval step, future systems will employ agents that "walk" the graph interactively.

* **Mechanism:** The agent will start at an entry point, inspect the neighbors, "reason" about which path to follow (e.g., "I need to check the database schema, so I will follow the imports edge to models.py"), and traverse the graph step-by-step. This moves the paradigm from "Search" to "Exploration," mimicking the workflow of a human engineer debugging a complex system.40

## **Conclusion**

The evolution of Code RAG from flat, text-based retrieval to structure-aware graph analysis represents a fundamental maturation of AI engineering tools. The evidence from 2024 and 2025 demonstrates unequivocally that **tracing code structure**—through ASTs, CFGs, and dependency graphs—is the key to unlocking repository-scale intelligence.

Methodologies like **RepoGraph**, **cAST**, and **GRACE** have successfully mapped the "manifold of code," allowing retrieval systems to respect the rigid logical dependencies that govern software execution. By replacing arbitrary text chunks with semantic graph nodes and replacing similarity search with ego-graph traversal, these systems have achieved dramatic improvements in benchmark performance, solving problems that were previously intractable for AI. As infrastructure tools like **LlamaIndex** and **Neo4j** continue to lower the barrier to entry, structural graph analysis is poised to become the standard architecture for all advanced software engineering agents.

## ---

**Appendix A: Implementation Reference for Graph Construction**

*Conceptual Schema for a Code Graph Node (JSON-LD Style)*

JSON

{  
  "@context": "http://schema.org/Code",  
  "@type": "Method",  
  "id": "src/auth/login.py::User::authenticate",  
  "name": "authenticate",  
  "code\_embedding": \[0.021, \-0.145, 0.332,...\],   
  "attributes": {  
    "visibility": "public",  
    "is\_async": true,  
    "return\_type": "Boolean",  
    "start\_line": 42,  
    "end\_line": 85  
  },  
  "relationships":  
}

This schema illustrates the fusion of structural data (lines, types), relational data (calls, imports), and semantic data (embeddings, similarity links) into a single queryable object, forming the atomic unit of the modern Code RAG system.

#### **Works cited**

1. cAST: Enhancing Code Retrieval-Augmented Generation ... \- arXiv, accessed January 22, 2026, [https://arxiv.org/abs/2506.15655](https://arxiv.org/abs/2506.15655)  
2. Retrieval-Augmented Code Generation: A Survey with Focus on Repository-Level Approaches \- arXiv, accessed January 22, 2026, [https://arxiv.org/html/2510.04905v1](https://arxiv.org/html/2510.04905v1)  
3. Understanding the Foundations of Repository-Level AI Software Engineering with RepoGraph \- Hao Hoang, accessed January 22, 2026, [https://haohoang.is-a.dev/post/repo-graph/](https://haohoang.is-a.dev/post/repo-graph/)  
4. GRACE: Graph-Guided Repository-Aware Code Completion through Hierarchical Code Fusion \- arXiv, accessed January 22, 2026, [https://arxiv.org/html/2509.05980v1](https://arxiv.org/html/2509.05980v1)  
5. Structural-Semantic Code Graph (SSCG) \- Emergent Mind, accessed January 22, 2026, [https://www.emergentmind.com/topics/structural-semantic-code-graph-sscg](https://www.emergentmind.com/topics/structural-semantic-code-graph-sscg)  
6. RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph \- arXiv, accessed January 22, 2026, [https://arxiv.org/html/2410.14684v1](https://arxiv.org/html/2410.14684v1)  
7. \[2507.16585\] LLMxCPG: Context-Aware Vulnerability Detection Through Code Property Graph-Guided Large Language Models \- arXiv, accessed January 22, 2026, [https://arxiv.org/abs/2507.16585](https://arxiv.org/abs/2507.16585)  
8. The Code Property Graph (CPG), accessed January 22, 2026, [https://3887453.fs1.hubspotusercontent-na1.net/hubfs/3887453/2025/White%20Papers/qwiet-ai\_cpg-data-sheet\_02.pdf](https://3887453.fs1.hubspotusercontent-na1.net/hubfs/3887453/2025/White%20Papers/qwiet-ai_cpg-data-sheet_02.pdf)  
9. \[2408.08921\] Graph Retrieval-Augmented Generation: A Survey \- arXiv, accessed January 22, 2026, [https://arxiv.org/abs/2408.08921](https://arxiv.org/abs/2408.08921)  
10. Graph Retrieval-Augmented Generation: A Survey \- arXiv, accessed January 22, 2026, [https://arxiv.org/pdf/2408.08921](https://arxiv.org/pdf/2408.08921)  
11. CAST: Enhancing Code Retrieval-Augmented Generation with Structural Chunking via Abstract Syntax Tree \- ACL Anthology, accessed January 22, 2026, [https://aclanthology.org/2025.findings-emnlp.430.pdf](https://aclanthology.org/2025.findings-emnlp.430.pdf)  
12. Early-Stage Graph Fusion with Refined Graph Neural Networks for Semantic Code Search, accessed January 22, 2026, [https://www.mdpi.com/2076-3417/16/1/12](https://www.mdpi.com/2076-3417/16/1/12)  
13. Semantic Code Graph – an information model to facilitate software comprehension \- arXiv, accessed January 22, 2026, [https://arxiv.org/html/2310.02128v2](https://arxiv.org/html/2310.02128v2)  
14. (PDF) RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph, accessed January 22, 2026, [https://www.researchgate.net/publication/385108343\_RepoGraph\_Enhancing\_AI\_Software\_Engineering\_with\_Repository-level\_Code\_Graph](https://www.researchgate.net/publication/385108343_RepoGraph_Enhancing_AI_Software_Engineering_with_Repository-level_Code_Graph)  
15. \[Literature Review\] GRACE: Graph-Guided Repository-Aware Code Completion through Hierarchical Code Fusion \- Moonlight, accessed January 22, 2026, [https://www.themoonlight.io/en/review/grace-graph-guided-repository-aware-code-completion-through-hierarchical-code-fusion](https://www.themoonlight.io/en/review/grace-graph-guided-repository-aware-code-completion-through-hierarchical-code-fusion)  
16. (PDF) GRACE: Graph-Guided Repository-Aware Code Completion through Hierarchical Code Fusion \- ResearchGate, accessed January 22, 2026, [https://www.researchgate.net/publication/395356159\_GRACE\_Graph-Guided\_Repository-Aware\_Code\_Completion\_through\_Hierarchical\_Code\_Fusion](https://www.researchgate.net/publication/395356159_GRACE_Graph-Guided_Repository-Aware_Code_Completion_through_Hierarchical_Code_Fusion)  
17. Production RAG: The Chunking, Retrieval, and Evaluation Strategies That Actually Work, accessed January 22, 2026, [https://towardsai.net/p/machine-learning/production-rag-the-chunking-retrieval-and-evaluation-strategies-that-actually-work](https://towardsai.net/p/machine-learning/production-rag-the-chunking-retrieval-and-evaluation-strategies-that-actually-work)  
18. Mastering Chunking Strategies for RAG: Best Practices & Code Examples \- Databricks Community, accessed January 22, 2026, [https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089)  
19. GraphRAG using Langchain and Oracle Graph on Oracle Database 23ai (Part 1\) \- Medium, accessed January 22, 2026, [https://medium.com/oracledevs/graphrag-using-langchain-and-oracle-graph-on-oracle-database-23ai-part-1-dc76b48a4ca1](https://medium.com/oracledevs/graphrag-using-langchain-and-oracle-graph-on-oracle-database-23ai-part-1-dc76b48a4ca1)  
20. Implementing Graph RAG Using Knowledge Graphs \- IBM, accessed January 22, 2026, [https://www.ibm.com/think/tutorials/knowledge-graph-rag](https://www.ibm.com/think/tutorials/knowledge-graph-rag)  
21. jsongraph/json-graph-specification: A proposal for representing graph structure (nodes / edges) in JSON. \- GitHub, accessed January 22, 2026, [https://github.com/jsongraph/json-graph-specification](https://github.com/jsongraph/json-graph-specification)  
22. JSON Graph Format Specification Website, accessed January 22, 2026, [https://jsongraphformat.info/](https://jsongraphformat.info/)  
23. REPOGRAPH: ENHANCING AI SOFTWARE ENGINEER- ING WITH REPOSITORY-LEVEL CODE GRAPH \- ICLR Proceedings, accessed January 22, 2026, [https://proceedings.iclr.cc/paper\_files/paper/2025/file/4a4a3c197deac042461c677219efd36c-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2025/file/4a4a3c197deac042461c677219efd36c-Paper-Conference.pdf)  
24. Recursive Retrieval for RAG: Implementation With LlamaIndex | DataCamp, accessed January 22, 2026, [https://www.datacamp.com/tutorial/recursive-retrieval-rag-llamaindex](https://www.datacamp.com/tutorial/recursive-retrieval-rag-llamaindex)  
25. Comparing Methods for Structured Retrieval (Auto-Retrieval vs. Recursive Retrieval) | LlamaIndex Python Documentation, accessed January 22, 2026, [https://developers.llamaindex.ai/python/examples/retrievers/auto\_vs\_recursive\_retriever/](https://developers.llamaindex.ai/python/examples/retrievers/auto_vs_recursive_retriever/)  
26. A Dummies guide to implementing Re-Ranking — Code walkthrough | by Rajesh Rajamani | primepartnerstech | Medium, accessed January 22, 2026, [https://medium.com/primepartnerstech/a-dummies-guide-to-implementing-re-ranking-code-walkthrough-c7d6705b6c22](https://medium.com/primepartnerstech/a-dummies-guide-to-implementing-re-ranking-code-walkthrough-c7d6705b6c22)  
27. Welcome \- GraphRAG, accessed January 22, 2026, [https://microsoft.github.io/graphrag/](https://microsoft.github.io/graphrag/)  
28. What is GraphRAG? Enhancing RAG with Knowledge Graphs \- Zilliz blog, accessed January 22, 2026, [https://zilliz.com/blog/graphrag-explained-enhance-rag-with-knowledge-graphs](https://zilliz.com/blog/graphrag-explained-enhance-rag-with-knowledge-graphs)  
29. CodeHierarchyAgentPack \- Llama Hub, accessed January 22, 2026, [https://llamahub.ai/l/llama-packs/llama-index-packs-code-hierarchy?from=](https://llamahub.ai/l/llama-packs/llama-index-packs-code-hierarchy?from)  
30. Hierarchical \- LlamaIndex, accessed January 22, 2026, [https://developers.llamaindex.ai/python/framework-api-reference/node\_parsers/hierarchical/](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/hierarchical/)  
31. Customizing property graph index in LlamaIndex, accessed January 22, 2026, [https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex](https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex)  
32. Log retriever traces \- Docs by LangChain, accessed January 22, 2026, [https://docs.langchain.com/langsmith/log-retriever-trace](https://docs.langchain.com/langsmith/log-retriever-trace)  
33. Build a custom RAG agent with LangGraph \- Docs by LangChain, accessed January 22, 2026, [https://docs.langchain.com/oss/javascript/langgraph/agentic-rag](https://docs.langchain.com/oss/javascript/langgraph/agentic-rag)  
34. What Is RDF? | Ontotext Fundamentals, accessed January 22, 2026, [https://www.ontotext.com/knowledgehub/fundamentals/what-is-rdf/](https://www.ontotext.com/knowledgehub/fundamentals/what-is-rdf/)  
35. RDF Schema 1.1 \- W3C, accessed January 22, 2026, [https://www.w3.org/TR/rdf-schema/](https://www.w3.org/TR/rdf-schema/)  
36. CodeRAG-Bench: Can Retrieval Augment Code Generation? \- arXiv, accessed January 22, 2026, [https://arxiv.org/html/2406.14497v2](https://arxiv.org/html/2406.14497v2)  
37. arXiv:2406.14497v2 \[cs.SE\] 26 Feb 2025, accessed January 22, 2026, [https://www.arxiv.org/pdf/2406.14497](https://www.arxiv.org/pdf/2406.14497)  
38. Advancing Retrieval-Augmented Generation for Structured Enterprise and Internal Data \- arXiv, accessed January 22, 2026, [https://arxiv.org/pdf/2507.12425](https://arxiv.org/pdf/2507.12425)  
39. microsoft/graphrag: A modular graph-based Retrieval-Augmented Generation (RAG) system, accessed January 22, 2026, [https://github.com/microsoft/graphrag](https://github.com/microsoft/graphrag)  
40. Building Knowledge Graph Agents With LlamaIndex Workflows \- Neo4j, accessed January 22, 2026, [https://neo4j.com/blog/knowledge-graph/knowledge-graph-agents-llamaindex/](https://neo4j.com/blog/knowledge-graph/knowledge-graph-agents-llamaindex/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAA3klEQVR4Xu2RqwoCQRSGj6CgeEcRBN/BZDFbLBaLGGziI/gEFrv4DmLWYtgomHwExWo1CF7+fy7LMs4Wm+AHXziX2T1zRuS3acIzvMOJU/ugCg/wBltOzcsVrmHSLfh4wambjOMJO5E4AVOROCQPL7BhYs59hFuYs02WHpzBNpzDDOzCPSxG+hRsXMEFzJocR6iHHQYWd6IvyPUNRX/ZC+fkvGU4hg+4lJgVcgPcBOFlAngSPcLI5BQ8zYfggxA7UgALcGDyioroFbFo6Ys+vBHPnksw7eT465qT+/Mdb4V+ITKqENUhAAAAAElFTkSuQmCC>
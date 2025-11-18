16:00:47 - Handling POST message
16:00:47 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:47 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"FAISS vector index inner product","k":2},"_meta":{"claudecode/toolUseId":"toolu_01QzV75fgtg23J9Wb5zm3vfC"}},"jsonrpc":"2.0","id":10}'
16:00:47 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'FAISS vector index inner product', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01QzV75fgtg23J9Wb5zm3vfC'}}, jsonrpc='2.0', id=10)
16:00:47 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'FAISS vector index inner product', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01QzV75fgtg23J9Wb5zm3vfC'}}, jsonrpc='2.0', id=10)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF598B50>))
INFO:     ::1:54446 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:47 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0BCEF90>
16:00:47 - Processing request of type CallToolRequest
16:00:47 - Dispatching request of type CallToolRequest
16:00:47 - [TOOL_CALL] search_code
16:00:47 - [SEARCH] query='FAISS vector index inner product', k=2, mode='auto'
16:00:47 - [ROUTING] Query: 'FAISS vector index inner product...' → bge_m3 (confidence: 0.03, reason: Low confidence (0.03 < 0.05) - using default (bge_m3))
16:00:47 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:47 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:00:47 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:00:47 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:47 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:00:47 - [INIT] BM25Index created successfully
16:00:47 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:00:47 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:47 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:47 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:47 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:00:48 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:00:48 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:00:48 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:00:48 - [INIT] Loaded existing dense index with 1445 vectors
16:00:48 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:48 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:48 - Attempting to populate HybridSearcher with existing dense index data
16:00:48 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:48 - Searcher initialized for project: claude-context-local
16:00:48 - [MULTI_HOP] Starting 2-hop search for 'FAISS vector index inner product' (k=2, expansion=0.3, mode=semantic)
16:00:48 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:48 - Search mode: semantic, hybrid enabled: True
16:00:48 - Index manager search called with k=4, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - [MULTI_HOP] Hop 1: Found 4 initial results (33.6ms)
16:00:48 - Index manager search called with k=2, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - Index manager search called with k=2, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 15.2ms)
16:00:48 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:00:48 - [MULTI_HOP] Complete: 2 results | Total=77ms (Hop1=34ms, Expansion=15ms, Rerank=27ms)
16:00:48 - Response sent
16:00:48 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=10, result={'content': [{'type': 'text', 'text': '{\n  "query": "FAISS vector index inner product",\n  "results": [\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "218-259",\n      "kind": "method",\n      "score": 0.8,\n      "chunk_id": "search\\\\indexer.py:218-259:method:_load_index"\n    },\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "51-54",\n      "kind": "method",\n      "score": 0.75,\n      "chunk_id": "search\\\\hybrid_searcher.py:51-54:method:estimate_batch_memory",\n      "graph": {\n        "calls": [\n          "int"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.027777777777777776,\n    "reason": "Low confidence (0.03 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.027777777777777776\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:00:48 - Handling POST message
16:00:48 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:48 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"how does the system work","k":2},"_meta":{"claudecode/toolUseId":"toolu_01NGSjgnhAgccDTcMhmi5hX3"}},"jsonrpc":"2.0","id":11}'
16:00:48 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'how does the system work', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01NGSjgnhAgccDTcMhmi5hX3'}}, jsonrpc='2.0', id=11)
16:00:48 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'how does the system work', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01NGSjgnhAgccDTcMhmi5hX3'}}, jsonrpc='2.0', id=11)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F2DF08D0>))
INFO:     ::1:54446 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:48 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE734990>
16:00:48 - Processing request of type CallToolRequest
16:00:48 - Dispatching request of type CallToolRequest
16:00:48 - [TOOL_CALL] search_code
16:00:48 - [SEARCH] query='how does the system work', k=2, mode='auto'
16:00:48 - [ROUTING] Query: 'how does the system work...' → bge_m3 (confidence: 0.04, reason: Low confidence (0.04 < 0.05) - using default (bge_m3))
16:00:48 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:48 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:00:48 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:00:48 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:48 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:00:48 - [INIT] BM25Index created successfully
16:00:48 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:00:48 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:48 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:48 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:48 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:00:48 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:00:48 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:00:48 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:00:48 - [INIT] Loaded existing dense index with 1445 vectors
16:00:48 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:48 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:48 - Attempting to populate HybridSearcher with existing dense index data
16:00:48 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:48 - Searcher initialized for project: claude-context-local
16:00:48 - [MULTI_HOP] Starting 2-hop search for 'how does the system work' (k=2, expansion=0.3, mode=semantic)
16:00:48 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:48 - Search mode: semantic, hybrid enabled: True
16:00:48 - Index manager search called with k=4, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - [MULTI_HOP] Hop 1: Found 4 initial results (16.7ms)
16:00:48 - Index manager search called with k=2, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - Index manager search called with k=2, filters=None
16:00:48 - Index has 1445 total vectors
16:00:48 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 0.0ms)
16:00:48 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:00:48 - [MULTI_HOP] Complete: 2 results | Total=50ms (Hop1=17ms, Expansion=0ms, Rerank=33ms)
16:00:48 - Response sent
16:00:48 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=11, result={'content': [{'type': 'text', 'text': '{\n  "query": "how does the system work",\n  "results": [\n    {\n      "file": "mcp_server\\\\server.py",\n      "lines": "692-738",\n      "kind": "function",\n      "score": 0.5,\n      "chunk_id": "mcp_server\\\\server.py:692-738:function:run_stdio_server"\n    },\n    {\n      "file": "mcp_server\\\\archived\\\\server_lowlevel_complete.py",\n      "lines": "652-704",\n      "kind": "function",\n      "score": 0.49,\n      "chunk_id": "mcp_server\\\\archived\\\\server_lowlevel_complete.py:652-704:function:app_lifespan"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.03773584905660377,\n    "reason": "Low confidence (0.04 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.027777777777777776\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:00:48 - Handling POST message
16:00:48 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:48 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"configure search mode hybrid bm25","k":2},"_meta":{"claudecode/toolUseId":"toolu_015U6zFiE8QXy5zKca1yn1oR"}},"jsonrpc":"2.0","id":12}'
16:00:48 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'configure search mode hybrid bm25', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015U6zFiE8QXy5zKca1yn1oR'}}, jsonrpc='2.0', id=12)
16:00:48 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'configure search mode hybrid bm25', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015U6zFiE8QXy5zKca1yn1oR'}}, jsonrpc='2.0', id=12)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BFB38BD0>))
INFO:     ::1:54446 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:48 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BFB39310>
16:00:48 - Processing request of type CallToolRequest
16:00:48 - Dispatching request of type CallToolRequest
16:00:48 - [TOOL_CALL] search_code
16:00:48 - [SEARCH] query='configure search mode hybrid bm25', k=2, mode='auto'
16:00:48 - [ROUTING] Query: 'configure search mode hybrid bm25...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:00:48 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:48 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:00:48 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:00:48 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:48 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:00:48 - [INIT] BM25Index created successfully
16:00:48 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:00:49 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:49 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:49 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:49 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:00:49 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:00:49 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:00:49 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:00:49 - [INIT] Loaded existing dense index with 1445 vectors
16:00:49 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:49 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:49 - Attempting to populate HybridSearcher with existing dense index data
16:00:49 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:49 - Searcher initialized for project: claude-context-local
16:00:49 - [MULTI_HOP] Starting 2-hop search for 'configure search mode hybrid bm25' (k=2, expansion=0.3, mode=semantic)
16:00:49 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:49 - Search mode: semantic, hybrid enabled: True
16:00:49 - Index manager search called with k=4, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - [MULTI_HOP] Hop 1: Found 4 initial results (19.9ms)
16:00:49 - Index manager search called with k=2, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - Index manager search called with k=2, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 16.5ms)
16:00:49 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:00:49 - [MULTI_HOP] Complete: 2 results | Total=62ms (Hop1=20ms, Expansion=16ms, Rerank=26ms)
16:00:49 - Response sent
16:00:49 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=12, result={'content': [{'type': 'text', 'text': '{\n  "query": "configure search mode hybrid bm25",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_tool_handlers.py",\n      "lines": "263-283",\n      "kind": "decorated_definition",\n      "score": 0.74,\n      "chunk_id": "tests\\\\unit\\\\test_tool_handlers.py:263-283:decorated_definition:test_handle_configure_search_mode"\n    },\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "429-538",\n      "kind": "method",\n      "score": 0.7,\n      "chunk_id": "search\\\\hybrid_searcher.py:429-538:method:_single_hop_search",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "bool",\n          "float",\n          "SearchResult"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.05555555555555555\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:00:49 - Handling POST message
16:00:49 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:49 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"Merkle tree hash calculation","k":2},"_meta":{"claudecode/toolUseId":"toolu_01XKkQAjhNDRikxSctuUdir7"}},"jsonrpc":"2.0","id":13}'
16:00:49 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'Merkle tree hash calculation', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01XKkQAjhNDRikxSctuUdir7'}}, jsonrpc='2.0', id=13)
16:00:49 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'Merkle tree hash calculation', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01XKkQAjhNDRikxSctuUdir7'}}, jsonrpc='2.0', id=13)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DEA015D0>))
INFO:     ::1:54446 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:49 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243EFC10350>
16:00:49 - Processing request of type CallToolRequest
16:00:49 - Dispatching request of type CallToolRequest
16:00:49 - [TOOL_CALL] search_code
16:00:49 - [SEARCH] query='Merkle tree hash calculation', k=2, mode='auto'
16:00:49 - [ROUTING] Query: 'Merkle tree hash calculation...' → coderankembed (confidence: 0.21, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.21)
16:00:49 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:49 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:00:49 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:00:49 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:49 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:00:49 - [INIT] BM25Index created successfully
16:00:49 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:00:49 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:49 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:49 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:49 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:00:49 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:00:49 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:00:49 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:00:49 - [INIT] Loaded existing dense index with 1445 vectors
16:00:49 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:49 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:49 - Attempting to populate HybridSearcher with existing dense index data
16:00:49 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:49 - Searcher initialized for project: claude-context-local
16:00:49 - [MULTI_HOP] Starting 2-hop search for 'Merkle tree hash calculation' (k=2, expansion=0.3, mode=semantic)
16:00:49 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:49 - Search mode: semantic, hybrid enabled: True
16:00:49 - Index manager search called with k=4, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - [MULTI_HOP] Hop 1: Found 4 initial results (33.5ms)
16:00:49 - Index manager search called with k=2, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - Index manager search called with k=2, filters=None
16:00:49 - Index has 1445 total vectors
16:00:49 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 0.0ms)
16:00:49 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:00:49 - [MULTI_HOP] Complete: 2 results | Total=69ms (Hop1=34ms, Expansion=0ms, Rerank=34ms)
16:00:49 - Response sent
16:00:49 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=13, result={'content': [{'type': 'text', 'text': '{\n  "query": "Merkle tree hash calculation",\n  "results": [\n    {\n      "file": "merkle\\\\merkle_dag.py",\n      "lines": "45-107",\n      "kind": "method",\n      "score": 0.77,\n      "chunk_id": "merkle\\\\merkle_dag.py:45-107:method:__init__",\n      "graph": {\n        "calls": [\n          "str",\n          "MerkleNode"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "merkle\\\\change_detector.py",\n      "lines": "45-253",\n      "kind": "class",\n      "score": 0.72,\n      "chunk_id": "merkle\\\\change_detector.py:45-253:class:ChangeDetector",\n      "graph": {\n        "calls": [\n          "SnapshotManager",\n          "MerkleDAG",\n          "FileChanges",\n          "str",\n          "bool"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.21428571428571427,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.21",\n    "scores": {\n      "coderankembed": 0.21428571428571427,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:00:50 - Handling POST message
16:00:50 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:50 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"what is semantic search","k":2},"_meta":{"claudecode/toolUseId":"toolu_01E3vGsQ2e7SXhXPPsU6P9jY"}},"jsonrpc":"2.0","id":14}'
16:00:50 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'what is semantic search', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01E3vGsQ2e7SXhXPPsU6P9jY'}}, jsonrpc='2.0', id=14)
16:00:50 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'what is semantic search', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01E3vGsQ2e7SXhXPPsU6P9jY'}}, jsonrpc='2.0', id=14)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF6D3F90>))
INFO:     ::1:54446 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:50 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BCF72AD0>
16:00:50 - Processing request of type CallToolRequest
16:00:50 - Dispatching request of type CallToolRequest
16:00:50 - [TOOL_CALL] search_code
16:00:50 - [SEARCH] query='what is semantic search', k=2, mode='auto'
16:00:50 - [ROUTING] Query: 'what is semantic search...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:00:50 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:50 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:00:50 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:00:50 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:50 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:00:50 - [INIT] BM25Index created successfully
16:00:50 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:00:50 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:50 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:50 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:50 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:00:50 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:00:50 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:00:50 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:00:50 - [INIT] Loaded existing dense index with 1445 vectors
16:00:50 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:50 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:50 - Attempting to populate HybridSearcher with existing dense index data
16:00:50 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:50 - Searcher initialized for project: claude-context-local
16:00:50 - [MULTI_HOP] Starting 2-hop search for 'what is semantic search' (k=2, expansion=0.3, mode=semantic)
16:00:50 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:50 - Search mode: semantic, hybrid enabled: True
16:00:50 - Index manager search called with k=4, filters=None
16:00:50 - Index has 1445 total vectors
16:00:50 - [MULTI_HOP] Hop 1: Found 4 initial results (26.1ms)
16:00:50 - Index manager search called with k=2, filters=None
16:00:50 - Index has 1445 total vectors
16:00:50 - Index manager search called with k=2, filters=None
16:00:50 - Index has 1445 total vectors
16:00:50 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 0.0ms)
16:00:50 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:00:50 - [MULTI_HOP] Complete: 2 results | Total=61ms (Hop1=26ms, Expansion=0ms, Rerank=34ms)
16:00:50 - Response sent
16:00:50 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=14, result={'content': [{'type': 'text', 'text': '{\n  "query": "what is semantic search",\n  "results": [\n    {\n      "file": "search\\\\searcher.py",\n      "lines": "102-126",\n      "kind": "method",\n      "score": 0.63,\n      "chunk_id": "search\\\\searcher.py:102-126:method:search",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "SearchResult"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\searcher.py",\n      "lines": "128-170",\n      "kind": "method",\n      "score": 0.59,\n      "chunk_id": "search\\\\searcher.py:128-170:method:_semantic_search",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "SearchResult"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:00:58 - Handling POST message
16:00:58 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:58 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"RRF reciprocal rank fusion reranking","k":2},"_meta":{"claudecode/toolUseId":"toolu_015dkuo88ypAzxJCJq7CLFuD"}},"jsonrpc":"2.0","id":15}'
16:00:58 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'RRF reciprocal rank fusion reranking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015dkuo88ypAzxJCJq7CLFuD'}}, jsonrpc='2.0', id=15)
16:00:58 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'RRF reciprocal rank fusion reranking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015dkuo88ypAzxJCJq7CLFuD'}}, jsonrpc='2.0', id=15)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F025A310>))
INFO:     ::1:54575 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:58 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242B8435750>
16:00:58 - Processing request of type CallToolRequest
16:00:58 - Dispatching request of type CallToolRequest
16:00:58 - [TOOL_CALL] search_code
16:00:58 - [SEARCH] query='RRF reciprocal rank fusion reranking', k=2, mode='auto'
16:00:58 - [ROUTING] Query: 'RRF reciprocal rank fusion reranking...' → coderankembed (confidence: 0.43, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.43)
16:00:58 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:58 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:00:58 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:00:58 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:58 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:00:58 - [INIT] BM25Index created successfully
16:00:58 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:00:59 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:59 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:59 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:00:59 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:00:59 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:00:59 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:00:59 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:00:59 - [INIT] Loaded existing dense index with 1445 vectors
16:00:59 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:59 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:59 - Attempting to populate HybridSearcher with existing dense index data
16:00:59 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:59 - Searcher initialized for project: claude-context-local
16:00:59 - [MULTI_HOP] Starting 2-hop search for 'RRF reciprocal rank fusion reranking' (k=2, expansion=0.3, mode=semantic)
16:00:59 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:59 - Search mode: semantic, hybrid enabled: True
16:00:59 - Index manager search called with k=4, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - [MULTI_HOP] Hop 1: Found 4 initial results (16.2ms)
16:00:59 - Index manager search called with k=2, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - Index manager search called with k=2, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 0.0ms)
16:00:59 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:00:59 - [MULTI_HOP] Complete: 2 results | Total=33ms (Hop1=16ms, Expansion=0ms, Rerank=15ms)
16:00:59 - Response sent
16:00:59 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=15, result={'content': [{'type': 'text', 'text': '{\n  "query": "RRF reciprocal rank fusion reranking",\n  "results": [\n    {\n      "file": "search\\\\reranker.py",\n      "lines": "20-311",\n      "kind": "class",\n      "score": 0.62,\n      "chunk_id": "search\\\\reranker.py:20-311:class:RRFReranker",\n      "graph": {\n        "calls": [\n          "int",\n          "float",\n          "SearchResult",\n          "str"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\reranker.py",\n      "lines": "23-34",\n      "kind": "method",\n      "score": 0.5,\n      "chunk_id": "search\\\\reranker.py:23-34:method:__init__",\n      "graph": {\n        "calls": [\n          "int",\n          "float"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.42857142857142855,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.43",\n    "scores": {\n      "coderankembed": 0.42857142857142855,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:00:59 - Handling POST message
16:00:59 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:59 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"setup installation environment","k":2},"_meta":{"claudecode/toolUseId":"toolu_01UkYit8sjMm1ML8grn4bbXA"}},"jsonrpc":"2.0","id":16}'
16:00:59 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'setup installation environment', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01UkYit8sjMm1ML8grn4bbXA'}}, jsonrpc='2.0', id=16)
16:00:59 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'setup installation environment', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01UkYit8sjMm1ML8grn4bbXA'}}, jsonrpc='2.0', id=16)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F1150990>))
INFO:     ::1:54575 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:59 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BCF72AD0>
16:00:59 - Processing request of type CallToolRequest
16:00:59 - Dispatching request of type CallToolRequest
16:00:59 - [TOOL_CALL] search_code
16:00:59 - [SEARCH] query='setup installation environment', k=2, mode='auto'
16:00:59 - [ROUTING] Query: 'setup installation environment...' → bge_m3 (confidence: 0.03, reason: Low confidence (0.03 < 0.05) - using default (bge_m3))
16:00:59 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:59 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:00:59 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:00:59 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:59 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:00:59 - [INIT] BM25Index created successfully
16:00:59 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:00:59 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:00:59 - [INIT] Loaded existing BM25 index with 1445 documents
16:00:59 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:59 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:00:59 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:00:59 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:00:59 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:00:59 - [INIT] Loaded existing dense index with 1445 vectors
16:00:59 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:00:59 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:00:59 - Attempting to populate HybridSearcher with existing dense index data
16:00:59 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:00:59 - Searcher initialized for project: claude-context-local
16:00:59 - [MULTI_HOP] Starting 2-hop search for 'setup installation environment' (k=2, expansion=0.3, mode=semantic)
16:00:59 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:00:59 - Search mode: semantic, hybrid enabled: True
16:00:59 - Index manager search called with k=4, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - [MULTI_HOP] Hop 1: Found 4 initial results (17.8ms)
16:00:59 - Index manager search called with k=2, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - Index manager search called with k=2, filters=None
16:00:59 - Index has 1445 total vectors
16:00:59 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 2.0ms)
16:00:59 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:00:59 - [MULTI_HOP] Complete: 2 results | Total=20ms (Hop1=18ms, Expansion=2ms, Rerank=0ms)
16:00:59 - Response sent
16:00:59 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=16, result={'content': [{'type': 'text', 'text': '{\n  "query": "setup installation environment",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_search_config.py",\n      "lines": "51-54",\n      "kind": "method",\n      "score": 0.93,\n      "chunk_id": "tests\\\\unit\\\\test_search_config.py:51-54:method:setup_method"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_stemming_integration.py",\n      "lines": "34-45",\n      "kind": "method",\n      "score": 0.83,\n      "chunk_id": "tests\\\\integration\\\\test_stemming_integration.py:34-45:method:setup_method"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.027777777777777776,\n    "reason": "Low confidence (0.03 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.027777777777777776\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:00:59 - Handling POST message
16:00:59 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:00:59 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"async def coroutine await","k":2},"_meta":{"claudecode/toolUseId":"toolu_01LNRgvJ6bn6DqjZYCJ86tzp"}},"jsonrpc":"2.0","id":17}'
16:00:59 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'async def coroutine await', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01LNRgvJ6bn6DqjZYCJ86tzp'}}, jsonrpc='2.0', id=17)
16:00:59 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'async def coroutine await', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01LNRgvJ6bn6DqjZYCJ86tzp'}}, jsonrpc='2.0', id=17)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F68943D0>))
INFO:     ::1:54575 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:00:59 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242B8435750>
16:00:59 - Processing request of type CallToolRequest
16:00:59 - Dispatching request of type CallToolRequest
16:00:59 - [TOOL_CALL] search_code
16:00:59 - [SEARCH] query='async def coroutine await', k=2, mode='auto'
16:00:59 - [ROUTING] Query: 'async def coroutine await...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:00:59 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:00:59 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:00:59 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:00:59 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:00:59 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:00:59 - [INIT] BM25Index created successfully
16:00:59 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:00 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:00 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:00 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:00 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:00 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:00 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:00 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:00 - [INIT] Loaded existing dense index with 1445 vectors
16:01:00 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:00 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:00 - Attempting to populate HybridSearcher with existing dense index data
16:01:00 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:00 - Searcher initialized for project: claude-context-local
16:01:00 - [MULTI_HOP] Starting 2-hop search for 'async def coroutine await' (k=2, expansion=0.3, mode=semantic)
16:01:00 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:00 - Search mode: semantic, hybrid enabled: True
16:01:00 - Index manager search called with k=4, filters=None
16:01:00 - Index has 1445 total vectors
16:01:00 - [MULTI_HOP] Hop 1: Found 4 initial results (16.0ms)
16:01:00 - Index manager search called with k=2, filters=None
16:01:00 - Index has 1445 total vectors
16:01:00 - Index manager search called with k=2, filters=None
16:01:00 - Index has 1445 total vectors
16:01:00 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 0.0ms)
16:01:00 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:01:00 - [MULTI_HOP] Complete: 2 results | Total=33ms (Hop1=16ms, Expansion=0ms, Rerank=17ms)
16:01:00 - Response sent
16:01:00 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=17, result={'content': [{'type': 'text', 'text': '{\n  "query": "async def coroutine await",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_tree_sitter.py",\n      "lines": "21-46",\n      "kind": "method",\n      "score": 0.67,\n      "chunk_id": "tests\\\\unit\\\\test_tree_sitter.py:21-46:method:test_function_chunking"\n    },\n    {\n      "file": "mcp_server\\\\server.py",\n      "lines": "754-763",\n      "kind": "function",\n      "score": 0.67,\n      "chunk_id": "mcp_server\\\\server.py:754-763:function:handle_sse"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:01:00 - Handling POST message
16:01:00 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:00 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"error handling exceptions try catch","k":2},"_meta":{"claudecode/toolUseId":"toolu_01EZdPhumiy7rZHv2sW1m3ug"}},"jsonrpc":"2.0","id":18}'
16:01:00 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'error handling exceptions try catch', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01EZdPhumiy7rZHv2sW1m3ug'}}, jsonrpc='2.0', id=18)
16:01:00 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'error handling exceptions try catch', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01EZdPhumiy7rZHv2sW1m3ug'}}, jsonrpc='2.0', id=18)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EFDCB590>))
INFO:     ::1:54575 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:00 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243EFDCAC10>
16:01:00 - Processing request of type CallToolRequest
16:01:00 - Dispatching request of type CallToolRequest
16:01:00 - [TOOL_CALL] search_code
16:01:00 - [SEARCH] query='error handling exceptions try catch', k=2, mode='auto'
16:01:00 - [ROUTING] Query: 'error handling exceptions try catch...' → qwen3 (confidence: 0.08, reason: Matched Implementation queries and algorithms with confidence 0.08)
16:01:00 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:00 - [ROUTING] Using routed model: Qwen/Qwen3-Embedding-0.6B (key: qwen3)
16:01:00 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:01:00 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:01:00 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:00 - [INIT] BM25Index created successfully
16:01:00 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:01:00 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:00 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:00 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:01:00 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:01:00 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:01:00 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:01:00 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:01:00 - [INIT] Loaded existing dense index with 1445 vectors
16:01:00 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:00 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:00 - Attempting to populate HybridSearcher with existing dense index data
16:01:00 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:00 - Searcher initialized for project: claude-context-local
16:01:00 - [MULTI_HOP] Starting 2-hop search for 'error handling exceptions try catch' (k=2, expansion=0.3, mode=semantic)
16:01:00 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:00 - Search mode: semantic, hybrid enabled: True
16:01:00 - Loading model: Qwen/Qwen3-Embedding-0.6B
16:01:00 - [VALIDATED CACHE] Enabling offline mode for faster startup.
16:01:00 - Loading model from validated cache: C:\Users\Inter\.claude_code_search\models\models--Qwen--Qwen3-Embedding-0.6B\snapshots\c54f2e6e80b2d7b7de06f51cec4959f6b3e03418
16:01:00 - [GPU_0] BEFORE_LOAD: Allocated=2.63GB, Reserved=2.69GB, Total=22.49GB (11.7% used)
16:01:00 - Load pretrained SentenceTransformer: C:\Users\Inter\.claude_code_search\models\models--Qwen--Qwen3-Embedding-0.6B\snapshots\c54f2e6e80b2d7b7de06f51cec4959f6b3e03418
16:01:01 - 1 prompt is loaded, with the key: query
16:01:01 - Model loaded successfully on device: cuda:0
16:01:01 - [GPU_0] AFTER_LOAD: Allocated=4.85GB, Reserved=4.91GB, Total=22.49GB (21.6% used)
16:01:01 - Index manager search called with k=4, filters=None
16:01:01 - Index has 1445 total vectors
16:01:01 - [MULTI_HOP] Hop 1: Found 4 initial results (1208.2ms)
16:01:01 - Index manager search called with k=2, filters=None
16:01:01 - Index has 1445 total vectors
16:01:01 - Index manager search called with k=2, filters=None
16:01:01 - Index has 1445 total vectors
16:01:01 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 2.0ms)
16:01:01 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:01 - [MULTI_HOP] Complete: 2 results | Total=1238ms (Hop1=1208ms, Expansion=2ms, Rerank=28ms)
16:01:01 - Response sent
16:01:01 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=18, result={'content': [{'type': 'text', 'text': '{\n  "query": "error handling exceptions try catch",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_call_graph_extraction.py",\n      "lines": "100-114",\n      "kind": "method",\n      "score": 0.83,\n      "chunk_id": "tests\\\\unit\\\\test_call_graph_extraction.py:100-114:method:test_extract_multiple_calls"\n    },\n    {\n      "file": "tests\\\\unit\\\\test_tool_handlers.py",\n      "lines": "371-386",\n      "kind": "decorated_definition",\n      "score": 0.62,\n      "chunk_id": "tests\\\\unit\\\\test_tool_handlers.py:371-386:decorated_definition:test_all_handlers_have_error_handling",\n      "graph": {\n        "calls": [\n          "inspect"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "qwen3",\n    "confidence": 0.07547169811320754,\n    "reason": "Matched Implementation queries and algorithms with confidence 0.08",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.07547169811320754,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:02 - Handling POST message
16:01:02 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:02 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"GPU CUDA tensor embedding model","k":2},"_meta":{"claudecode/toolUseId":"toolu_01VKT5yBpNjJt3NA3HYnYbUQ"}},"jsonrpc":"2.0","id":19}'
16:01:02 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'GPU CUDA tensor embedding model', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01VKT5yBpNjJt3NA3HYnYbUQ'}}, jsonrpc='2.0', id=19)
16:01:02 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'GPU CUDA tensor embedding model', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01VKT5yBpNjJt3NA3HYnYbUQ'}}, jsonrpc='2.0', id=19)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F0E77910>))
INFO:     ::1:54575 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:02 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0E81B50>
16:01:02 - Processing request of type CallToolRequest
16:01:02 - Dispatching request of type CallToolRequest
16:01:02 - [TOOL_CALL] search_code
16:01:02 - [SEARCH] query='GPU CUDA tensor embedding model', k=2, mode='auto'
16:01:02 - [ROUTING] Query: 'GPU CUDA tensor embedding model...' → bge_m3 (confidence: 0.06, reason: Matched Workflow and configuration queries with confidence 0.06)
16:01:02 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:02 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:02 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:02 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:02 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:02 - [INIT] BM25Index created successfully
16:01:02 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:02 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:02 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:02 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:02 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:02 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:02 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:02 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:02 - [INIT] Loaded existing dense index with 1445 vectors
16:01:02 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:02 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:02 - Attempting to populate HybridSearcher with existing dense index data
16:01:02 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:02 - Searcher initialized for project: claude-context-local
16:01:02 - [MULTI_HOP] Starting 2-hop search for 'GPU CUDA tensor embedding model' (k=2, expansion=0.3, mode=semantic)
16:01:02 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:02 - Search mode: semantic, hybrid enabled: True
16:01:02 - Index manager search called with k=4, filters=None
16:01:02 - Index has 1445 total vectors
16:01:02 - [MULTI_HOP] Hop 1: Found 4 initial results (24.1ms)
16:01:02 - Index manager search called with k=2, filters=None
16:01:02 - Index has 1445 total vectors
16:01:02 - Index manager search called with k=2, filters=None
16:01:02 - Index has 1445 total vectors
16:01:02 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 0.0ms)
16:01:02 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:02 - [MULTI_HOP] Complete: 2 results | Total=59ms (Hop1=24ms, Expansion=0ms, Rerank=34ms)
16:01:02 - Response sent
16:01:02 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=19, result={'content': [{'type': 'text', 'text': '{\n  "query": "GPU CUDA tensor embedding model",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_model_selection.py",\n      "lines": "131-185",\n      "kind": "class",\n      "score": 0.84,\n      "chunk_id": "tests\\\\unit\\\\test_model_selection.py:131-185:class:TestCodeEmbedderModelSupport"\n    },\n    {\n      "file": "embeddings\\\\embedder.py",\n      "lines": "38-1061",\n      "kind": "class",\n      "score": 0.6,\n      "chunk_id": "embeddings\\\\embedder.py:38-1061:class:CodeEmbedder",\n      "graph": {\n        "calls": [\n          "str",\n          "CodeChunk",\n          "int",\n          "EmbeddingResult",\n          "np.ndarray",\n          "Path",\n          "tuple",\n          "bool",\n          "list",\n          "search.config.get_model_registry",\n          "search.config.get_model_config",\n          "shutil",\n          "json",\n          "search.config.get_search_config",\n          "huggingface_hub.model_info",\n          "search.config.MODEL_REGISTRY"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.05555555555555555,\n    "reason": "Matched Workflow and configuration queries with confidence 0.06",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.05555555555555555\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:26 - Handling POST message
16:01:26 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:26 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"parse python source code into AST","k":2},"_meta":{"claudecode/toolUseId":"toolu_01Q2jT9T48u8g3YGeb2SMwFA"}},"jsonrpc":"2.0","id":20}'
16:01:26 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'parse python source code into AST', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01Q2jT9T48u8g3YGeb2SMwFA'}}, jsonrpc='2.0', id=20)
16:01:26 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'parse python source code into AST', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01Q2jT9T48u8g3YGeb2SMwFA'}}, jsonrpc='2.0', id=20)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451F40750>))
INFO:     ::1:52285 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:26 - Received message: <mcp.shared.session.RequestResponder object at 0x0000024451F39410>
16:01:26 - Processing request of type CallToolRequest
16:01:26 - Dispatching request of type CallToolRequest
16:01:26 - [TOOL_CALL] search_code
16:01:26 - [SEARCH] query='parse python source code into AST', k=2, mode='auto'
16:01:26 - [ROUTING] Query: 'parse python source code into AST...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:01:26 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:26 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:26 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:26 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:26 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:26 - [INIT] BM25Index created successfully
16:01:26 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:26 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:26 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:26 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:26 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:26 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:26 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:26 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:26 - [INIT] Loaded existing dense index with 1445 vectors
16:01:26 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:26 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:26 - Attempting to populate HybridSearcher with existing dense index data
16:01:26 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:26 - Searcher initialized for project: claude-context-local
16:01:26 - [MULTI_HOP] Starting 2-hop search for 'parse python source code into AST' (k=2, expansion=0.3, mode=semantic)
16:01:26 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:26 - Search mode: semantic, hybrid enabled: True
16:01:26 - Index manager search called with k=4, filters=None
16:01:26 - Index has 1445 total vectors
16:01:26 - [MULTI_HOP] Hop 1: Found 4 initial results (31.0ms)
16:01:26 - Index manager search called with k=2, filters=None
16:01:26 - Index has 1445 total vectors
16:01:26 - Index manager search called with k=2, filters=None
16:01:26 - Index has 1445 total vectors
16:01:26 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 6.4ms)
16:01:26 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:01:26 - [MULTI_HOP] Complete: 2 results | Total=66ms (Hop1=31ms, Expansion=6ms, Rerank=28ms)
16:01:26 - Response sent
16:01:26 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=20, result={'content': [{'type': 'text', 'text': '{\n  "query": "parse python source code into AST",\n  "results": [\n    {\n      "file": "graph\\\\call_graph_extractor.py",\n      "lines": "209-233",\n      "kind": "method",\n      "score": 0.81,\n      "chunk_id": "graph\\\\call_graph_extractor.py:209-233:method:extract_calls_from_ast_node",\n      "graph": {\n        "calls": [\n          "ast.AST",\n          "str",\n          "CallEdge"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "graph\\\\relationship_extractors\\\\inheritance_extractor.py",\n      "lines": "20-283",\n      "kind": "class",\n      "score": 0.77,\n      "chunk_id": "graph\\\\relationship_extractors\\\\inheritance_extractor.py:20-283:class:InheritanceExtractor",\n      "graph": {\n        "calls": [\n          "BaseRelationshipExtractor",\n          "str",\n          "RelationshipEdge",\n          "ast.AST",\n          "ast.ClassDef",\n          "ast.Attribute",\n          "bool",\n          "int"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:26 - Handling POST message
16:01:26 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:26 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"generate embeddings for code chunks","k":2},"_meta":{"claudecode/toolUseId":"toolu_015HMnYBVrpHFwMxqwjDMgwz"}},"jsonrpc":"2.0","id":21}'
16:01:26 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'generate embeddings for code chunks', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015HMnYBVrpHFwMxqwjDMgwz'}}, jsonrpc='2.0', id=21)
16:01:26 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'generate embeddings for code chunks', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_015HMnYBVrpHFwMxqwjDMgwz'}}, jsonrpc='2.0', id=21)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451A06F10>))
INFO:     ::1:52285 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:26 - Received message: <mcp.shared.session.RequestResponder object at 0x0000024451A064D0>
16:01:26 - Processing request of type CallToolRequest
16:01:26 - Dispatching request of type CallToolRequest
16:01:26 - [TOOL_CALL] search_code
16:01:26 - [SEARCH] query='generate embeddings for code chunks', k=2, mode='auto'
16:01:26 - [ROUTING] Query: 'generate embeddings for code chunks...' → bge_m3 (confidence: 0.08, reason: Matched Workflow and configuration queries with confidence 0.08)
16:01:26 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:26 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:26 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:26 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:26 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:26 - [INIT] BM25Index created successfully
16:01:26 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:26 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:26 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:26 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:26 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:27 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:27 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:27 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:27 - [INIT] Loaded existing dense index with 1445 vectors
16:01:27 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:27 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:27 - Attempting to populate HybridSearcher with existing dense index data
16:01:27 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:27 - Searcher initialized for project: claude-context-local
16:01:27 - [MULTI_HOP] Starting 2-hop search for 'generate embeddings for code chunks' (k=2, expansion=0.3, mode=semantic)
16:01:27 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:27 - Search mode: semantic, hybrid enabled: True
16:01:27 - Index manager search called with k=4, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - [MULTI_HOP] Hop 1: Found 4 initial results (40.7ms)
16:01:27 - Index manager search called with k=2, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - Index manager search called with k=2, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 4.9ms)
16:01:27 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:01:27 - [MULTI_HOP] Complete: 2 results | Total=85ms (Hop1=41ms, Expansion=5ms, Rerank=34ms)
16:01:27 - Response sent
16:01:27 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=21, result={'content': [{'type': 'text', 'text': '{\n  "query": "generate embeddings for code chunks",\n  "results": [\n    {\n      "file": "embeddings\\\\embedder.py",\n      "lines": "482-576",\n      "kind": "method",\n      "score": 0.75,\n      "chunk_id": "embeddings\\\\embedder.py:482-576:method:embed_chunks",\n      "graph": {\n        "calls": [\n          "CodeChunk",\n          "int",\n          "EmbeddingResult",\n          "search.config.get_search_config"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "embeddings\\\\embedder.py",\n      "lines": "427-480",\n      "kind": "method",\n      "score": 0.74,\n      "chunk_id": "embeddings\\\\embedder.py:427-480:method:embed_chunk",\n      "graph": {\n        "calls": [\n          "CodeChunk",\n          "EmbeddingResult"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.08333333333333333,\n    "reason": "Matched Workflow and configuration queries with confidence 0.08",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.08333333333333333\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:27 - Handling POST message
16:01:27 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:27 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"normalize file paths cross platform","k":2},"_meta":{"claudecode/toolUseId":"toolu_01RAoazRALfz92uWLJmhrGjZ"}},"jsonrpc":"2.0","id":22}'
16:01:27 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'normalize file paths cross platform', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RAoazRALfz92uWLJmhrGjZ'}}, jsonrpc='2.0', id=22)
16:01:27 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'normalize file paths cross platform', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RAoazRALfz92uWLJmhrGjZ'}}, jsonrpc='2.0', id=22)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F2134ED0>))
INFO:     ::1:52285 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:27 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F2134110>
16:01:27 - Processing request of type CallToolRequest
16:01:27 - Dispatching request of type CallToolRequest
16:01:27 - [TOOL_CALL] search_code
16:01:27 - [SEARCH] query='normalize file paths cross platform', k=2, mode='auto'
16:01:27 - [ROUTING] Query: 'normalize file paths cross platform...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:01:27 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:27 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:27 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:27 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:27 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:27 - [INIT] BM25Index created successfully
16:01:27 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:27 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:27 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:27 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:27 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:27 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:27 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:27 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:27 - [INIT] Loaded existing dense index with 1445 vectors
16:01:27 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:27 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:27 - Attempting to populate HybridSearcher with existing dense index data
16:01:27 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:27 - Searcher initialized for project: claude-context-local
16:01:27 - [MULTI_HOP] Starting 2-hop search for 'normalize file paths cross platform' (k=2, expansion=0.3, mode=semantic)
16:01:27 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:27 - Search mode: semantic, hybrid enabled: True
16:01:27 - Index manager search called with k=4, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - [MULTI_HOP] Hop 1: Found 4 initial results (30.9ms)
16:01:27 - Index manager search called with k=2, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - Index manager search called with k=2, filters=None
16:01:27 - Index has 1445 total vectors
16:01:27 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 2.0ms)
16:01:27 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:27 - [MULTI_HOP] Complete: 2 results | Total=57ms (Hop1=31ms, Expansion=2ms, Rerank=24ms)
16:01:27 - Response sent
16:01:27 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=22, result={'content': [{'type': 'text', 'text': '{\n  "query": "normalize file paths cross platform",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_path_normalization.py",\n      "lines": "22-26",\n      "kind": "method",\n      "score": 0.84,\n      "chunk_id": "tests\\\\unit\\\\test_path_normalization.py:22-26:method:test_normalize_backslash_to_forward_slash"\n    },\n    {\n      "file": "tests\\\\unit\\\\test_path_normalization.py",\n      "lines": "170-208",\n      "kind": "class",\n      "score": 0.64,\n      "chunk_id": "tests\\\\unit\\\\test_path_normalization.py:170-208:class:TestCrossPlatformPaths"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:01:27 - Handling POST message
16:01:27 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:27 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"extract function calls from python","k":2},"_meta":{"claudecode/toolUseId":"toolu_01RfPr36qRxmV4SKoQwcrwtM"}},"jsonrpc":"2.0","id":23}'
16:01:27 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'extract function calls from python', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RfPr36qRxmV4SKoQwcrwtM'}}, jsonrpc='2.0', id=23)
16:01:27 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'extract function calls from python', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RfPr36qRxmV4SKoQwcrwtM'}}, jsonrpc='2.0', id=23)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DE138A50>))
INFO:     ::1:52285 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:27 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE139B10>
16:01:27 - Processing request of type CallToolRequest
16:01:27 - Dispatching request of type CallToolRequest
16:01:27 - [TOOL_CALL] search_code
16:01:27 - [SEARCH] query='extract function calls from python', k=2, mode='auto'
16:01:27 - [ROUTING] Query: 'extract function calls from python...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:01:27 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:27 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:27 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:27 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:27 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:27 - [INIT] BM25Index created successfully
16:01:27 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:28 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:28 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:28 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:28 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:28 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:28 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:28 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:28 - [INIT] Loaded existing dense index with 1445 vectors
16:01:28 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:28 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:28 - Attempting to populate HybridSearcher with existing dense index data
16:01:28 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:28 - Searcher initialized for project: claude-context-local
16:01:28 - [MULTI_HOP] Starting 2-hop search for 'extract function calls from python' (k=2, expansion=0.3, mode=semantic)
16:01:28 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:28 - Search mode: semantic, hybrid enabled: True
16:01:28 - Index manager search called with k=4, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - [MULTI_HOP] Hop 1: Found 4 initial results (40.9ms)
16:01:28 - Index manager search called with k=2, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - Index manager search called with k=2, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 2.0ms)
16:01:28 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:01:28 - [MULTI_HOP] Complete: 2 results | Total=75ms (Hop1=41ms, Expansion=2ms, Rerank=32ms)
16:01:28 - Response sent
16:01:28 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=23, result={'content': [{'type': 'text', 'text': '{\n  "query": "extract function calls from python",\n  "results": [\n    {\n      "file": "graph\\\\call_graph_extractor.py",\n      "lines": "93-126",\n      "kind": "method",\n      "score": 0.74,\n      "chunk_id": "graph\\\\call_graph_extractor.py:93-126:method:extract_calls",\n      "graph": {\n        "calls": [\n          "str",\n          "CallEdge"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "graph\\\\call_graph_extractor.py",\n      "lines": "65-78",\n      "kind": "method",\n      "score": 0.72,\n      "chunk_id": "graph\\\\call_graph_extractor.py:65-78:method:extract_calls",\n      "graph": {\n        "calls": [\n          "str",\n          "CallEdge"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:28 - Handling POST message
16:01:28 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:28 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"search using BM25 sparse retrieval","k":2},"_meta":{"claudecode/toolUseId":"toolu_01QNw45LaGAhe1yuamjrKxt4"}},"jsonrpc":"2.0","id":24}'
16:01:28 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search using BM25 sparse retrieval', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01QNw45LaGAhe1yuamjrKxt4'}}, jsonrpc='2.0', id=24)
16:01:28 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search using BM25 sparse retrieval', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01QNw45LaGAhe1yuamjrKxt4'}}, jsonrpc='2.0', id=24)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F09F0610>))
INFO:     ::1:52285 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:28 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F09F1650>
16:01:28 - Processing request of type CallToolRequest
16:01:28 - Dispatching request of type CallToolRequest
16:01:28 - [TOOL_CALL] search_code
16:01:28 - [SEARCH] query='search using BM25 sparse retrieval', k=2, mode='auto'
16:01:28 - [ROUTING] Query: 'search using BM25 sparse retrieval...' → bge_m3 (confidence: 0.04, reason: Low confidence (0.04 < 0.05) - using default (bge_m3))
16:01:28 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:28 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:28 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:28 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:28 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:28 - [INIT] BM25Index created successfully
16:01:28 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:28 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:28 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:28 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:28 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:28 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:28 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:28 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:28 - [INIT] Loaded existing dense index with 1445 vectors
16:01:28 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:28 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:28 - Attempting to populate HybridSearcher with existing dense index data
16:01:28 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:28 - Searcher initialized for project: claude-context-local
16:01:28 - [MULTI_HOP] Starting 2-hop search for 'search using BM25 sparse retrieval' (k=2, expansion=0.3, mode=semantic)
16:01:28 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:28 - Search mode: semantic, hybrid enabled: True
16:01:28 - Index manager search called with k=4, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - [MULTI_HOP] Hop 1: Found 4 initial results (30.5ms)
16:01:28 - Index manager search called with k=2, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - Index manager search called with k=2, filters=None
16:01:28 - Index has 1445 total vectors
16:01:28 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 9.2ms)
16:01:28 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:01:28 - [MULTI_HOP] Complete: 2 results | Total=67ms (Hop1=31ms, Expansion=9ms, Rerank=27ms)
16:01:28 - Response sent
16:01:28 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=24, result={'content': [{'type': 'text', 'text': '{\n  "query": "search using BM25 sparse retrieval",\n  "results": [\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "850-867",\n      "kind": "method",\n      "score": 0.67,\n      "chunk_id": "search\\\\hybrid_searcher.py:850-867:method:_search_bm25",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "float"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\bm25_index.py",\n      "lines": "315-360",\n      "kind": "method",\n      "score": 0.67,\n      "chunk_id": "search\\\\bm25_index.py:315-360:method:search",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "float"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.03773584905660377,\n    "reason": "Low confidence (0.04 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:36 - Handling POST message
16:01:36 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:36 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"load FAISS index from disk","k":2},"_meta":{"claudecode/toolUseId":"toolu_011oH5SrZyf7UGCeoajNZXwD"}},"jsonrpc":"2.0","id":25}'
16:01:36 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'load FAISS index from disk', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_011oH5SrZyf7UGCeoajNZXwD'}}, jsonrpc='2.0', id=25)
16:01:36 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'load FAISS index from disk', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_011oH5SrZyf7UGCeoajNZXwD'}}, jsonrpc='2.0', id=25)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024452674D50>))
INFO:     ::1:52409 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:36 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0572850>
16:01:36 - Processing request of type CallToolRequest
16:01:36 - Dispatching request of type CallToolRequest
16:01:36 - [TOOL_CALL] search_code
16:01:36 - [SEARCH] query='load FAISS index from disk', k=2, mode='auto'
16:01:36 - [ROUTING] Query: 'load FAISS index from disk...' → bge_m3 (confidence: 0.06, reason: Matched Workflow and configuration queries with confidence 0.06)
16:01:36 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:36 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:36 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:36 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:36 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:36 - [INIT] BM25Index created successfully
16:01:36 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:36 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:36 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:36 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:36 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:36 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:36 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:36 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:36 - [INIT] Loaded existing dense index with 1445 vectors
16:01:36 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:36 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:36 - Attempting to populate HybridSearcher with existing dense index data
16:01:36 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:36 - Searcher initialized for project: claude-context-local
16:01:36 - [MULTI_HOP] Starting 2-hop search for 'load FAISS index from disk' (k=2, expansion=0.3, mode=semantic)
16:01:36 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:36 - Search mode: semantic, hybrid enabled: True
16:01:37 - Index manager search called with k=4, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - [MULTI_HOP] Hop 1: Found 4 initial results (31.8ms)
16:01:37 - Index manager search called with k=2, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - Index manager search called with k=2, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 5.0ms)
16:01:37 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:01:37 - [MULTI_HOP] Complete: 2 results | Total=70ms (Hop1=32ms, Expansion=5ms, Rerank=26ms)
16:01:37 - Response sent
16:01:37 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=25, result={'content': [{'type': 'text', 'text': '{\n  "query": "load FAISS index from disk",\n  "results": [\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "218-259",\n      "kind": "method",\n      "score": 0.67,\n      "chunk_id": "search\\\\indexer.py:218-259:method:_load_index"\n    },\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "794-865",\n      "kind": "method",\n      "score": 0.65,\n      "chunk_id": "search\\\\indexer.py:794-865:method:save_index",\n      "graph": {\n        "calls": [\n          "json"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.05555555555555555,\n    "reason": "Matched Workflow and configuration queries with confidence 0.06",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.05555555555555555\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:37 - Handling POST message
16:01:37 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:37 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"calculate similarity scores ranking","k":2},"_meta":{"claudecode/toolUseId":"toolu_01YQ93T6on5w1FMP5jYK1seR"}},"jsonrpc":"2.0","id":26}'
16:01:37 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'calculate similarity scores ranking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01YQ93T6on5w1FMP5jYK1seR'}}, jsonrpc='2.0', id=26)
16:01:37 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'calculate similarity scores ranking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01YQ93T6on5w1FMP5jYK1seR'}}, jsonrpc='2.0', id=26)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BFD3ACD0>))
INFO:     ::1:52409 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:37 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE8C9B90>
16:01:37 - Processing request of type CallToolRequest
16:01:37 - Dispatching request of type CallToolRequest
16:01:37 - [TOOL_CALL] search_code
16:01:37 - [SEARCH] query='calculate similarity scores ranking', k=2, mode='auto'
16:01:37 - [ROUTING] Query: 'calculate similarity scores ranking...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:01:37 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:37 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:37 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:37 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:37 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:37 - [INIT] BM25Index created successfully
16:01:37 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:37 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:37 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:37 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:37 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:37 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:37 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:37 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:37 - [INIT] Loaded existing dense index with 1445 vectors
16:01:37 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:37 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:37 - Attempting to populate HybridSearcher with existing dense index data
16:01:37 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:37 - Searcher initialized for project: claude-context-local
16:01:37 - [MULTI_HOP] Starting 2-hop search for 'calculate similarity scores ranking' (k=2, expansion=0.3, mode=semantic)
16:01:37 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:37 - Search mode: semantic, hybrid enabled: True
16:01:37 - Index manager search called with k=4, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - [MULTI_HOP] Hop 1: Found 4 initial results (35.4ms)
16:01:37 - Index manager search called with k=2, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - Index manager search called with k=2, filters=None
16:01:37 - Index has 1445 total vectors
16:01:37 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 4.0ms)
16:01:37 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:37 - [MULTI_HOP] Complete: 2 results | Total=67ms (Hop1=35ms, Expansion=4ms, Rerank=28ms)
16:01:37 - Response sent
16:01:37 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=26, result={'content': [{'type': 'text', 'text': '{\n  "query": "calculate similarity scores ranking",\n  "results": [\n    {\n      "file": "tests\\\\integration\\\\test_multi_hop_flow.py",\n      "lines": "364-401",\n      "kind": "method",\n      "score": 0.78,\n      "chunk_id": "tests\\\\integration\\\\test_multi_hop_flow.py:364-401:method:test_multi_hop_reranking"\n    },\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "756-808",\n      "kind": "method",\n      "score": 0.64,\n      "chunk_id": "search\\\\hybrid_searcher.py:756-808:method:_rerank_by_query",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "numpy"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:37 - Handling POST message
16:01:37 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:37 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"handle MCP tool requests","k":2},"_meta":{"claudecode/toolUseId":"toolu_01XLLckgYfBJbgR3ugAEJjF7"}},"jsonrpc":"2.0","id":27}'
16:01:37 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'handle MCP tool requests', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01XLLckgYfBJbgR3ugAEJjF7'}}, jsonrpc='2.0', id=27)
16:01:37 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'handle MCP tool requests', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01XLLckgYfBJbgR3ugAEJjF7'}}, jsonrpc='2.0', id=27)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x000002445280F790>))
INFO:     ::1:52409 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:37 - Received message: <mcp.shared.session.RequestResponder object at 0x000002445280E610>
16:01:37 - Processing request of type CallToolRequest
16:01:37 - Dispatching request of type CallToolRequest
16:01:37 - [TOOL_CALL] search_code
16:01:37 - [SEARCH] query='handle MCP tool requests', k=2, mode='auto'
16:01:37 - [ROUTING] Query: 'handle MCP tool requests...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:01:37 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:37 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:37 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:37 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:37 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:37 - [INIT] BM25Index created successfully
16:01:37 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:38 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:38 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:38 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:38 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:38 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:38 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:38 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:38 - [INIT] Loaded existing dense index with 1445 vectors
16:01:38 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:38 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:38 - Attempting to populate HybridSearcher with existing dense index data
16:01:38 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:38 - Searcher initialized for project: claude-context-local
16:01:38 - [MULTI_HOP] Starting 2-hop search for 'handle MCP tool requests' (k=2, expansion=0.3, mode=semantic)
16:01:38 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:38 - Search mode: semantic, hybrid enabled: True
16:01:38 - Index manager search called with k=4, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - [MULTI_HOP] Hop 1: Found 4 initial results (38.0ms)
16:01:38 - Index manager search called with k=2, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - Index manager search called with k=2, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 4.6ms)
16:01:38 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:38 - [MULTI_HOP] Complete: 2 results | Total=72ms (Hop1=38ms, Expansion=5ms, Rerank=28ms)
16:01:38 - Response sent
16:01:38 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=27, result={'content': [{'type': 'text', 'text': '{\n  "query": "handle MCP tool requests",\n  "results": [\n    {\n      "file": "scripts\\\\manual_configure.py",\n      "lines": "98-176",\n      "kind": "method",\n      "score": 0.76,\n      "chunk_id": "scripts\\\\manual_configure.py:98-176:method:add_mcp_server",\n      "graph": {\n        "calls": [\n          "str",\n          "list",\n          "bool"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "mcp_server\\\\tools\\\\__init__.py",\n      "lines": "1-9",\n      "kind": "module",\n      "score": 0.66,\n      "chunk_id": "mcp_server\\\\tools\\\\__init__.py:1-9:module",\n      "graph": {\n        "calls": [\n          "mcp_server.tools.code_relationship_analyzer.CodeRelationshipAnalyzer",\n          "mcp_server.tools.code_relationship_analyzer.ImpactReport"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:38 - Handling POST message
16:01:38 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:38 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"chunk source code into pieces","k":2},"_meta":{"claudecode/toolUseId":"toolu_01SQJehr7AbZahodkHiQd6Yp"}},"jsonrpc":"2.0","id":28}'
16:01:38 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'chunk source code into pieces', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01SQJehr7AbZahodkHiQd6Yp'}}, jsonrpc='2.0', id=28)
16:01:38 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'chunk source code into pieces', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01SQJehr7AbZahodkHiQd6Yp'}}, jsonrpc='2.0', id=28)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451BB3A90>))
INFO:     ::1:52409 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:38 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F09B9C10>
16:01:38 - Processing request of type CallToolRequest
16:01:38 - Dispatching request of type CallToolRequest
16:01:38 - [TOOL_CALL] search_code
16:01:38 - [SEARCH] query='chunk source code into pieces', k=2, mode='auto'
16:01:38 - [ROUTING] Query: 'chunk source code into pieces...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:01:38 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:38 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:38 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:38 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:38 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:38 - [INIT] BM25Index created successfully
16:01:38 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:38 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:38 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:38 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:38 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:38 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:38 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:38 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:38 - [INIT] Loaded existing dense index with 1445 vectors
16:01:38 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:38 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:38 - Attempting to populate HybridSearcher with existing dense index data
16:01:38 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:38 - Searcher initialized for project: claude-context-local
16:01:38 - [MULTI_HOP] Starting 2-hop search for 'chunk source code into pieces' (k=2, expansion=0.3, mode=semantic)
16:01:38 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:38 - Search mode: semantic, hybrid enabled: True
16:01:38 - Index manager search called with k=4, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - [MULTI_HOP] Hop 1: Found 4 initial results (23.6ms)
16:01:38 - Index manager search called with k=2, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - Index manager search called with k=2, filters=None
16:01:38 - Index has 1445 total vectors
16:01:38 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 8.8ms)
16:01:38 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:01:38 - [MULTI_HOP] Complete: 2 results | Total=49ms (Hop1=24ms, Expansion=9ms, Rerank=16ms)
16:01:38 - Response sent
16:01:38 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=28, result={'content': [{'type': 'text', 'text': '{\n  "query": "chunk source code into pieces",\n  "results": [\n    {\n      "file": "chunking\\\\multi_language_chunker.py",\n      "lines": "231-410",\n      "kind": "method",\n      "score": 0.82,\n      "chunk_id": "chunking\\\\multi_language_chunker.py:231-410:method:_convert_tree_chunks",\n      "graph": {\n        "calls": [\n          "TreeSitterChunk",\n          "str",\n          "CodeChunk"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "chunking\\\\__init__.py",\n      "lines": "1-1",\n      "kind": "module",\n      "score": 0.72,\n      "chunk_id": "chunking\\\\__init__.py:1-1:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:39 - Handling POST message
16:01:39 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:39 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"build merkle tree for files","k":2},"_meta":{"claudecode/toolUseId":"toolu_01UCFVTpGhoXybn8speYbUDy"}},"jsonrpc":"2.0","id":29}'
16:01:39 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'build merkle tree for files', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01UCFVTpGhoXybn8speYbUDy'}}, jsonrpc='2.0', id=29)
16:01:39 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'build merkle tree for files', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01UCFVTpGhoXybn8speYbUDy'}}, jsonrpc='2.0', id=29)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF787E90>))
INFO:     ::1:52409 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:39 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0D50F90>
16:01:39 - Processing request of type CallToolRequest
16:01:39 - Dispatching request of type CallToolRequest
16:01:39 - [TOOL_CALL] search_code
16:01:39 - [SEARCH] query='build merkle tree for files', k=2, mode='auto'
16:01:39 - [ROUTING] Query: 'build merkle tree for files...' → coderankembed (confidence: 0.21, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.21)
16:01:39 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:39 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:01:39 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:01:39 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:01:39 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:01:39 - [INIT] BM25Index created successfully
16:01:39 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:01:39 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:39 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:39 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:01:39 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:01:39 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:01:39 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:01:39 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:01:39 - [INIT] Loaded existing dense index with 1445 vectors
16:01:39 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:39 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:39 - Attempting to populate HybridSearcher with existing dense index data
16:01:39 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:39 - Searcher initialized for project: claude-context-local
16:01:39 - [MULTI_HOP] Starting 2-hop search for 'build merkle tree for files' (k=2, expansion=0.3, mode=semantic)
16:01:39 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:39 - Search mode: semantic, hybrid enabled: True
16:01:39 - Index manager search called with k=4, filters=None
16:01:39 - Index has 1445 total vectors
16:01:39 - [MULTI_HOP] Hop 1: Found 4 initial results (25.0ms)
16:01:39 - Index manager search called with k=2, filters=None
16:01:39 - Index has 1445 total vectors
16:01:39 - Index manager search called with k=2, filters=None
16:01:39 - Index has 1445 total vectors
16:01:39 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 9.9ms)
16:01:39 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:39 - [MULTI_HOP] Complete: 2 results | Total=57ms (Hop1=25ms, Expansion=10ms, Rerank=22ms)
16:01:39 - Response sent
16:01:39 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=29, result={'content': [{'type': 'text', 'text': '{\n  "query": "build merkle tree for files",\n  "results": [\n    {\n      "file": "merkle\\\\merkle_dag.py",\n      "lines": "298-307",\n      "kind": "method",\n      "score": 0.61,\n      "chunk_id": "merkle\\\\merkle_dag.py:298-307:method:find_node",\n      "graph": {\n        "calls": [\n          "str",\n          "MerkleNode"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "merkle\\\\merkle_dag.py",\n      "lines": "228-235",\n      "kind": "method",\n      "score": 0.5,\n      "chunk_id": "merkle\\\\merkle_dag.py:228-235:method:build"\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.21428571428571427,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.21",\n    "scores": {\n      "coderankembed": 0.21428571428571427,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:01:59 - Handling POST message
16:01:59 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:01:59 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for embedding generation model","k":2},"_meta":{"claudecode/toolUseId":"toolu_01BiHeSGgMJnxv1gdFXeE9yq"}},"jsonrpc":"2.0","id":30}'
16:01:59 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for embedding generation model', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01BiHeSGgMJnxv1gdFXeE9yq'}}, jsonrpc='2.0', id=30)
16:01:59 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for embedding generation model', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01BiHeSGgMJnxv1gdFXeE9yq'}}, jsonrpc='2.0', id=30)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF107310>))
INFO:     ::1:51455 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:01:59 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0BBDC10>
16:01:59 - Processing request of type CallToolRequest
16:01:59 - Dispatching request of type CallToolRequest
16:01:59 - [TOOL_CALL] search_code
16:01:59 - [SEARCH] query='class for embedding generation model', k=2, mode='auto'
16:01:59 - [ROUTING] Query: 'class for embedding generation model...' → bge_m3 (confidence: 0.08, reason: Matched Workflow and configuration queries with confidence 0.08)
16:01:59 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:01:59 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:01:59 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:01:59 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:59 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:01:59 - [INIT] BM25Index created successfully
16:01:59 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:01:59 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:01:59 - [INIT] Loaded existing BM25 index with 1445 documents
16:01:59 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:01:59 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:01:59 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:01:59 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:01:59 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:01:59 - [INIT] Loaded existing dense index with 1445 vectors
16:01:59 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:01:59 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:01:59 - Attempting to populate HybridSearcher with existing dense index data
16:01:59 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:01:59 - Searcher initialized for project: claude-context-local
16:01:59 - [MULTI_HOP] Starting 2-hop search for 'class for embedding generation model' (k=2, expansion=0.3, mode=semantic)
16:01:59 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:01:59 - Search mode: semantic, hybrid enabled: True
16:01:59 - Index manager search called with k=4, filters=None
16:01:59 - Index has 1445 total vectors
16:01:59 - [MULTI_HOP] Hop 1: Found 4 initial results (25.9ms)
16:01:59 - Index manager search called with k=2, filters=None
16:01:59 - Index has 1445 total vectors
16:01:59 - Index manager search called with k=2, filters=None
16:01:59 - Index has 1445 total vectors
16:01:59 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 13.5ms)
16:01:59 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:01:59 - [MULTI_HOP] Complete: 2 results | Total=61ms (Hop1=26ms, Expansion=13ms, Rerank=22ms)
16:01:59 - Response sent
16:01:59 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=30, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for embedding generation model",\n  "results": [\n    {\n      "file": "tests\\\\integration\\\\test_model_switching.py",\n      "lines": "39-47",\n      "kind": "method",\n      "score": 0.92,\n      "chunk_id": "tests\\\\integration\\\\test_model_switching.py:39-47:method:test_gemma_chunk_embedding"\n    },\n    {\n      "file": "embeddings\\\\__init__.py",\n      "lines": "1-2",\n      "kind": "module",\n      "score": 0.73,\n      "chunk_id": "embeddings\\\\__init__.py:1-2:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.08333333333333333,\n    "reason": "Matched Workflow and configuration queries with confidence 0.08",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.08333333333333333\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:02:00 - Handling POST message
16:02:00 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:00 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for hybrid search combining BM25","k":2},"_meta":{"claudecode/toolUseId":"toolu_01RJrqkALAwmLqK2Ro2LUA5f"}},"jsonrpc":"2.0","id":31}'
16:02:00 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for hybrid search combining BM25', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RJrqkALAwmLqK2Ro2LUA5f'}}, jsonrpc='2.0', id=31)
16:02:00 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for hybrid search combining BM25', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01RJrqkALAwmLqK2Ro2LUA5f'}}, jsonrpc='2.0', id=31)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF7C09D0>))
INFO:     ::1:51455 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:00 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243EF7C2650>
16:02:00 - Processing request of type CallToolRequest
16:02:00 - Dispatching request of type CallToolRequest
16:02:00 - [TOOL_CALL] search_code
16:02:00 - [SEARCH] query='class for hybrid search combining BM25', k=2, mode='auto'
16:02:00 - [ROUTING] Query: 'class for hybrid search combining BM25...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:02:00 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:00 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:02:00 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:02:00 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:00 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:02:00 - [INIT] BM25Index created successfully
16:02:00 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:02:00 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:00 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:00 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:00 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:02:00 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:02:00 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:02:00 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:02:00 - [INIT] Loaded existing dense index with 1445 vectors
16:02:00 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:00 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:00 - Attempting to populate HybridSearcher with existing dense index data
16:02:00 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:00 - Searcher initialized for project: claude-context-local
16:02:00 - [MULTI_HOP] Starting 2-hop search for 'class for hybrid search combining BM25' (k=2, expansion=0.3, mode=semantic)
16:02:00 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:00 - Search mode: semantic, hybrid enabled: True
16:02:00 - Index manager search called with k=4, filters=None
16:02:00 - Index has 1445 total vectors
16:02:00 - [MULTI_HOP] Hop 1: Found 4 initial results (22.3ms)
16:02:00 - Index manager search called with k=2, filters=None
16:02:00 - Index has 1445 total vectors
16:02:00 - Index manager search called with k=2, filters=None
16:02:00 - Index has 1445 total vectors
16:02:00 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 7.7ms)
16:02:00 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:02:00 - [MULTI_HOP] Complete: 2 results | Total=44ms (Hop1=22ms, Expansion=8ms, Rerank=12ms)
16:02:00 - Response sent
16:02:00 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=31, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for hybrid search combining BM25",\n  "results": [\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "57-1400",\n      "kind": "class",\n      "score": 0.68,\n      "chunk_id": "search\\\\hybrid_searcher.py:57-1400:class:HybridSearcher",\n      "graph": {\n        "calls": [\n          "str",\n          "float",\n          "int",\n          "bool",\n          "SearchResult",\n          "set",\n          "numpy",\n          "embeddings.embedder.EmbeddingResult",\n          ".config.get_search_config",\n          ".searcher.SearchResult",\n          ".config.SearchConfigManager",\n          "pathlib.Path",\n          "embeddings.embedder.CodeEmbedder",\n          "traceback",\n          ".reranker.SearchResult"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "60-179",\n      "kind": "method",\n      "score": 0.61,\n      "chunk_id": "search\\\\hybrid_searcher.py:60-179:method:__init__",\n      "graph": {\n        "calls": [\n          "str",\n          "float",\n          "int",\n          "bool"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.05660377358490566,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:00 - Handling POST message
16:02:00 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:00 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for incremental indexing changes","k":2},"_meta":{"claudecode/toolUseId":"toolu_011Husf5RBW822K7sHZu11oc"}},"jsonrpc":"2.0","id":32}'
16:02:00 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for incremental indexing changes', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_011Husf5RBW822K7sHZu11oc'}}, jsonrpc='2.0', id=32)
16:02:00 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for incremental indexing changes', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_011Husf5RBW822K7sHZu11oc'}}, jsonrpc='2.0', id=32)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F034ED50>))
INFO:     ::1:51455 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:00 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F034FBD0>
16:02:00 - Processing request of type CallToolRequest
16:02:00 - Dispatching request of type CallToolRequest
16:02:00 - [TOOL_CALL] search_code
16:02:00 - [SEARCH] query='class for incremental indexing changes', k=2, mode='auto'
16:02:00 - [ROUTING] Query: 'class for incremental indexing changes...' → bge_m3 (confidence: 0.08, reason: Matched Workflow and configuration queries with confidence 0.08)
16:02:00 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:00 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:02:00 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:02:00 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:00 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:00 - [INIT] BM25Index created successfully
16:02:00 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:02:00 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:00 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:00 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:00 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:02:00 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:02:00 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:02:00 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:02:00 - [INIT] Loaded existing dense index with 1445 vectors
16:02:00 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:00 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:00 - Attempting to populate HybridSearcher with existing dense index data
16:02:00 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:00 - Searcher initialized for project: claude-context-local
16:02:00 - [MULTI_HOP] Starting 2-hop search for 'class for incremental indexing changes' (k=2, expansion=0.3, mode=semantic)
16:02:00 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:00 - Search mode: semantic, hybrid enabled: True
16:02:01 - Index manager search called with k=4, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - [MULTI_HOP] Hop 1: Found 4 initial results (31.1ms)
16:02:01 - Index manager search called with k=2, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - Index manager search called with k=2, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 0.0ms)
16:02:01 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:02:01 - [MULTI_HOP] Complete: 2 results | Total=64ms (Hop1=31ms, Expansion=0ms, Rerank=33ms)
16:02:01 - Response sent
16:02:01 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=32, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for incremental indexing changes",\n  "results": [\n    {\n      "file": "search\\\\incremental_indexer.py",\n      "lines": "50-69",\n      "kind": "method",\n      "score": 0.9,\n      "chunk_id": "search\\\\incremental_indexer.py:50-69:method:__init__",\n      "graph": {\n        "calls": [\n          "Indexer",\n          "CodeEmbedder",\n          "MultiLanguageChunker",\n          "SnapshotManager"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_incremental_indexer.py",\n      "lines": "34-60",\n      "kind": "method",\n      "score": 0.8,\n      "chunk_id": "tests\\\\unit\\\\test_incremental_indexer.py:34-60:method:test_result_to_dict"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.08333333333333333,\n    "reason": "Matched Workflow and configuration queries with confidence 0.08",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.08333333333333333\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:01 - Handling POST message
16:02:01 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:01 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for tree-sitter parsing","k":2},"_meta":{"claudecode/toolUseId":"toolu_01MEjGS15phccRjEJ9gvGs89"}},"jsonrpc":"2.0","id":33}'
16:02:01 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for tree-sitter parsing', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01MEjGS15phccRjEJ9gvGs89'}}, jsonrpc='2.0', id=33)
16:02:01 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for tree-sitter parsing', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01MEjGS15phccRjEJ9gvGs89'}}, jsonrpc='2.0', id=33)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F2D25950>))
INFO:     ::1:51455 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:01 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F2D268D0>
16:02:01 - Processing request of type CallToolRequest
16:02:01 - Dispatching request of type CallToolRequest
16:02:01 - [TOOL_CALL] search_code
16:02:01 - [SEARCH] query='class for tree-sitter parsing', k=2, mode='auto'
16:02:01 - [ROUTING] Query: 'class for tree-sitter parsing...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:02:01 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:01 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:02:01 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:02:01 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:01 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:02:01 - [INIT] BM25Index created successfully
16:02:01 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:02:01 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:01 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:01 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:01 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:02:01 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:02:01 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:02:01 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:02:01 - [INIT] Loaded existing dense index with 1445 vectors
16:02:01 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:01 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:01 - Attempting to populate HybridSearcher with existing dense index data
16:02:01 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:01 - Searcher initialized for project: claude-context-local
16:02:01 - [MULTI_HOP] Starting 2-hop search for 'class for tree-sitter parsing' (k=2, expansion=0.3, mode=semantic)
16:02:01 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:01 - Search mode: semantic, hybrid enabled: True
16:02:01 - Index manager search called with k=4, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - [MULTI_HOP] Hop 1: Found 4 initial results (20.3ms)
16:02:01 - Index manager search called with k=2, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - Index manager search called with k=2, filters=None
16:02:01 - Index has 1445 total vectors
16:02:01 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 7.8ms)
16:02:01 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:02:01 - [MULTI_HOP] Complete: 2 results | Total=52ms (Hop1=20ms, Expansion=8ms, Rerank=23ms)
16:02:01 - Response sent
16:02:01 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=33, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for tree-sitter parsing",\n  "results": [\n    {\n      "file": "chunking\\\\tree_sitter.py",\n      "lines": "652-704",\n      "kind": "class",\n      "score": 0.87,\n      "chunk_id": "chunking\\\\tree_sitter.py:652-704:class:JavaChunker",\n      "graph": {\n        "calls": [\n          "LanguageChunker",\n          "str",\n          "bytes"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "chunking\\\\tree_sitter.py",\n      "lines": "138-152",\n      "kind": "method",\n      "score": 0.66,\n      "chunk_id": "chunking\\\\tree_sitter.py:138-152:method:__init__",\n      "graph": {\n        "calls": [\n          "str"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:01 - Handling POST message
16:02:01 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:01 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for query routing models","k":2},"_meta":{"claudecode/toolUseId":"toolu_01CowzFvjDz9EueTfJuJeuo2"}},"jsonrpc":"2.0","id":34}'
16:02:01 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for query routing models', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01CowzFvjDz9EueTfJuJeuo2'}}, jsonrpc='2.0', id=34)
16:02:01 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for query routing models', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01CowzFvjDz9EueTfJuJeuo2'}}, jsonrpc='2.0', id=34)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x000002445246DF50>))
INFO:     ::1:51455 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:01 - Received message: <mcp.shared.session.RequestResponder object at 0x000002445246E410>
16:02:01 - Processing request of type CallToolRequest
16:02:01 - Dispatching request of type CallToolRequest
16:02:01 - [TOOL_CALL] search_code
16:02:01 - [SEARCH] query='class for query routing models', k=2, mode='auto'
16:02:01 - [ROUTING] Query: 'class for query routing models...' → bge_m3 (confidence: 0.04, reason: Low confidence (0.04 < 0.05) - using default (bge_m3))
16:02:01 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:01 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:02:01 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:02:01 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:01 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:01 - [INIT] BM25Index created successfully
16:02:01 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:02:02 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:02 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:02 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:02 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:02:02 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:02:02 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:02:02 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:02:02 - [INIT] Loaded existing dense index with 1445 vectors
16:02:02 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:02 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:02 - Attempting to populate HybridSearcher with existing dense index data
16:02:02 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:02 - Searcher initialized for project: claude-context-local
16:02:02 - [MULTI_HOP] Starting 2-hop search for 'class for query routing models' (k=2, expansion=0.3, mode=semantic)
16:02:02 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:02 - Search mode: semantic, hybrid enabled: True
16:02:02 - Index manager search called with k=4, filters=None
16:02:02 - Index has 1445 total vectors
16:02:02 - [MULTI_HOP] Hop 1: Found 4 initial results (29.9ms)
16:02:02 - Index manager search called with k=2, filters=None
16:02:02 - Index has 1445 total vectors
16:02:02 - Index manager search called with k=2, filters=None
16:02:02 - Index has 1445 total vectors
16:02:02 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 0.0ms)
16:02:02 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:02:02 - [MULTI_HOP] Complete: 2 results | Total=64ms (Hop1=30ms, Expansion=0ms, Rerank=33ms)
16:02:02 - Response sent
16:02:02 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=34, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for query routing models",\n  "results": [\n    {\n      "file": "search\\\\query_router.py",\n      "lines": "196-254",\n      "kind": "method",\n      "score": 0.73,\n      "chunk_id": "search\\\\query_router.py:196-254:method:route",\n      "graph": {\n        "calls": [\n          "str",\n          "float",\n          "RoutingDecision"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\query_router.py",\n      "lines": "24-306",\n      "kind": "class",\n      "score": 0.65,\n      "chunk_id": "search\\\\query_router.py:24-306:class:QueryRouter",\n      "graph": {\n        "calls": [\n          "bool",\n          "str",\n          "float",\n          "RoutingDecision",\n          "list"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.03773584905660377,\n    "reason": "Low confidence (0.04 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:09 - Handling POST message
16:02:09 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:09 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for BM25 index management","k":2},"_meta":{"claudecode/toolUseId":"toolu_012vaKjJJHgQo2BMJ7Sf1jei"}},"jsonrpc":"2.0","id":35}'
16:02:09 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for BM25 index management', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_012vaKjJJHgQo2BMJ7Sf1jei'}}, jsonrpc='2.0', id=35)
16:02:09 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for BM25 index management', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_012vaKjJJHgQo2BMJ7Sf1jei'}}, jsonrpc='2.0', id=35)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BF0D37D0>))
INFO:     ::1:51579 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:09 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE5E6790>
16:02:09 - Processing request of type CallToolRequest
16:02:09 - Dispatching request of type CallToolRequest
16:02:09 - [TOOL_CALL] search_code
16:02:09 - [SEARCH] query='class for BM25 index management', k=2, mode='auto'
16:02:09 - [ROUTING] Query: 'class for BM25 index management...' → bge_m3 (confidence: 0.04, reason: Low confidence (0.04 < 0.05) - using default (bge_m3))
16:02:09 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:09 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:02:09 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:02:09 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:09 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:09 - [INIT] BM25Index created successfully
16:02:09 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:02:09 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:09 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:09 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:09 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:02:09 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:02:09 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:02:09 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:02:09 - [INIT] Loaded existing dense index with 1445 vectors
16:02:09 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:09 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:09 - Attempting to populate HybridSearcher with existing dense index data
16:02:09 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:09 - Searcher initialized for project: claude-context-local
16:02:09 - [MULTI_HOP] Starting 2-hop search for 'class for BM25 index management' (k=2, expansion=0.3, mode=semantic)
16:02:09 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:09 - Search mode: semantic, hybrid enabled: True
16:02:09 - Index manager search called with k=4, filters=None
16:02:09 - Index has 1445 total vectors
16:02:09 - [MULTI_HOP] Hop 1: Found 4 initial results (34.1ms)
16:02:09 - Index manager search called with k=2, filters=None
16:02:09 - Index has 1445 total vectors
16:02:09 - Index manager search called with k=2, filters=None
16:02:09 - Index has 1445 total vectors
16:02:09 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 3.9ms)
16:02:09 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:02:09 - [MULTI_HOP] Complete: 2 results | Total=62ms (Hop1=34ms, Expansion=4ms, Rerank=23ms)
16:02:09 - Response sent
16:02:09 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=35, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for BM25 index management",\n  "results": [\n    {\n      "file": "search\\\\bm25_index.py",\n      "lines": "167-200",\n      "kind": "method",\n      "score": 0.86,\n      "chunk_id": "search\\\\bm25_index.py:167-200:method:__init__",\n      "graph": {\n        "calls": [\n          "str",\n          "bool"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_bm25_index.py",\n      "lines": "130-143",\n      "kind": "method",\n      "score": 0.8,\n      "chunk_id": "tests\\\\unit\\\\test_bm25_index.py:130-143:method:setup_method"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.03773584905660377,\n    "reason": "Low confidence (0.04 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.027777777777777776\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:10 - Handling POST message
16:02:10 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:10 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for graph storage networkx","k":2},"_meta":{"claudecode/toolUseId":"toolu_019tGfDw9YQdYBLPWSkgJ6nK"}},"jsonrpc":"2.0","id":36}'
16:02:10 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for graph storage networkx', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_019tGfDw9YQdYBLPWSkgJ6nK'}}, jsonrpc='2.0', id=36)
16:02:10 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for graph storage networkx', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_019tGfDw9YQdYBLPWSkgJ6nK'}}, jsonrpc='2.0', id=36)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BF961110>))
INFO:     ::1:51579 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:10 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BF960650>
16:02:10 - Processing request of type CallToolRequest
16:02:10 - Dispatching request of type CallToolRequest
16:02:10 - [TOOL_CALL] search_code
16:02:10 - [SEARCH] query='class for graph storage networkx', k=2, mode='auto'
16:02:10 - [ROUTING] Query: 'class for graph storage networkx...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:02:10 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:10 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:02:10 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:02:10 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:10 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:02:10 - [INIT] BM25Index created successfully
16:02:10 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:02:10 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:10 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:10 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:10 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:02:10 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:02:10 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:02:10 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:02:10 - [INIT] Loaded existing dense index with 1445 vectors
16:02:10 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:10 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:10 - Attempting to populate HybridSearcher with existing dense index data
16:02:10 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:10 - Searcher initialized for project: claude-context-local
16:02:10 - [MULTI_HOP] Starting 2-hop search for 'class for graph storage networkx' (k=2, expansion=0.3, mode=semantic)
16:02:10 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:10 - Search mode: semantic, hybrid enabled: True
16:02:10 - Index manager search called with k=4, filters=None
16:02:10 - Index has 1445 total vectors
16:02:10 - [MULTI_HOP] Hop 1: Found 4 initial results (15.9ms)
16:02:10 - Index manager search called with k=2, filters=None
16:02:10 - Index has 1445 total vectors
16:02:10 - Index manager search called with k=2, filters=None
16:02:10 - Index has 1445 total vectors
16:02:10 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 2.7ms)
16:02:10 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:02:10 - [MULTI_HOP] Complete: 2 results | Total=31ms (Hop1=16ms, Expansion=3ms, Rerank=12ms)
16:02:10 - Response sent
16:02:10 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=36, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for graph storage networkx",\n  "results": [\n    {\n      "file": "graph\\\\graph_storage.py",\n      "lines": "18-449",\n      "kind": "class",\n      "score": 0.68,\n      "chunk_id": "graph\\\\graph_storage.py:18-449:class:CodeGraphStorage",\n      "graph": {\n        "calls": [\n          "str",\n          "Path",\n          "int",\n          "bool",\n          "RelationshipEdge"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "graph\\\\graph_storage.py",\n      "lines": "30-63",\n      "kind": "method",\n      "score": 0.62,\n      "chunk_id": "graph\\\\graph_storage.py:30-63:method:__init__",\n      "graph": {\n        "calls": [\n          "str",\n          "Path"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:10 - Handling POST message
16:02:10 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:10 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for multi-language chunking","k":2},"_meta":{"claudecode/toolUseId":"toolu_01Pzd6K55CEDydubrRApxrBb"}},"jsonrpc":"2.0","id":37}'
16:02:10 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for multi-language chunking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01Pzd6K55CEDydubrRApxrBb'}}, jsonrpc='2.0', id=37)
16:02:10 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for multi-language chunking', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01Pzd6K55CEDydubrRApxrBb'}}, jsonrpc='2.0', id=37)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF2A4A10>))
INFO:     ::1:51579 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:10 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243EF2A74D0>
16:02:10 - Processing request of type CallToolRequest
16:02:10 - Dispatching request of type CallToolRequest
16:02:10 - [TOOL_CALL] search_code
16:02:10 - [SEARCH] query='class for multi-language chunking', k=2, mode='auto'
16:02:10 - [ROUTING] Query: 'class for multi-language chunking...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:02:10 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:10 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:02:10 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:02:10 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:10 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:10 - [INIT] BM25Index created successfully
16:02:10 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:02:10 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:10 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:10 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:10 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:02:10 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:02:10 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:02:10 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:02:10 - [INIT] Loaded existing dense index with 1445 vectors
16:02:10 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:10 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:10 - Attempting to populate HybridSearcher with existing dense index data
16:02:10 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:10 - Searcher initialized for project: claude-context-local
16:02:10 - [MULTI_HOP] Starting 2-hop search for 'class for multi-language chunking' (k=2, expansion=0.3, mode=semantic)
16:02:10 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:10 - Search mode: semantic, hybrid enabled: True
16:02:10 - Index manager search called with k=4, filters=None
16:02:10 - Index has 1445 total vectors
16:02:11 - [MULTI_HOP] Hop 1: Found 4 initial results (49.1ms)
16:02:11 - Index manager search called with k=2, filters=None
16:02:11 - Index has 1445 total vectors
16:02:11 - Index manager search called with k=2, filters=None
16:02:11 - Index has 1445 total vectors
16:02:11 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 5, 1.0ms)
16:02:11 - [MULTI_HOP] Re-ranking 5 total chunks by query relevance
16:02:11 - [MULTI_HOP] Complete: 2 results | Total=76ms (Hop1=49ms, Expansion=1ms, Rerank=26ms)
16:02:11 - Response sent
16:02:11 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=37, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for multi-language chunking",\n  "results": [\n    {\n      "file": "tests\\\\integration\\\\test_mcp_functionality.py",\n      "lines": "58-94",\n      "kind": "function",\n      "score": 0.83,\n      "chunk_id": "tests\\\\integration\\\\test_mcp_functionality.py:58-94:function:test_chunking_core",\n      "graph": {\n        "calls": [\n          "tempfile",\n          "chunking.multi_language_chunker.MultiLanguageChunker"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_multi_language.py",\n      "lines": "10-201",\n      "kind": "class",\n      "score": 0.73,\n      "chunk_id": "tests\\\\unit\\\\test_multi_language.py:10-201:class:TestMultiLanguageChunker"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:11 - Handling POST message
16:02:11 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:11 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for snapshot management merkle","k":2},"_meta":{"claudecode/toolUseId":"toolu_01DFezw7EUtJoLAhBSN1L3Pz"}},"jsonrpc":"2.0","id":38}'
16:02:11 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for snapshot management merkle', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01DFezw7EUtJoLAhBSN1L3Pz'}}, jsonrpc='2.0', id=38)
16:02:11 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for snapshot management merkle', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01DFezw7EUtJoLAhBSN1L3Pz'}}, jsonrpc='2.0', id=38)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF300B10>))
INFO:     ::1:51579 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:11 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243EF301A10>
16:02:11 - Processing request of type CallToolRequest
16:02:11 - Dispatching request of type CallToolRequest
16:02:11 - [TOOL_CALL] search_code
16:02:11 - [SEARCH] query='class for snapshot management merkle', k=2, mode='auto'
16:02:11 - [ROUTING] Query: 'class for snapshot management merkle...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:02:11 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:11 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:02:11 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:02:11 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:11 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:02:11 - [INIT] BM25Index created successfully
16:02:11 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:02:11 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:11 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:11 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:02:11 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:02:11 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:02:11 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:02:11 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:02:11 - [INIT] Loaded existing dense index with 1445 vectors
16:02:11 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:11 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:11 - Attempting to populate HybridSearcher with existing dense index data
16:02:11 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:11 - Searcher initialized for project: claude-context-local
16:02:11 - [MULTI_HOP] Starting 2-hop search for 'class for snapshot management merkle' (k=2, expansion=0.3, mode=semantic)
16:02:11 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:11 - Search mode: semantic, hybrid enabled: True
16:02:11 - Index manager search called with k=4, filters=None
16:02:11 - Index has 1445 total vectors
16:02:11 - [MULTI_HOP] Hop 1: Found 4 initial results (25.2ms)
16:02:11 - Index manager search called with k=2, filters=None
16:02:11 - Index has 1445 total vectors
16:02:11 - Index manager search called with k=2, filters=None
16:02:11 - Index has 1445 total vectors
16:02:11 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 4, 6.8ms)
16:02:11 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:02:11 - [MULTI_HOP] Complete: 2 results | Total=80ms (Hop1=25ms, Expansion=7ms, Rerank=32ms)
16:02:11 - Response sent
16:02:11 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=38, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for snapshot management merkle",\n  "results": [\n    {\n      "file": "merkle\\\\snapshot_manager.py",\n      "lines": "12-346",\n      "kind": "class",\n      "score": 0.62,\n      "chunk_id": "merkle\\\\snapshot_manager.py:12-346:class:SnapshotManager",\n      "graph": {\n        "calls": [\n          "Path",\n          "str",\n          "int",\n          "MerkleDAG",\n          "bool",\n          "float",\n          "sys",\n          "pathlib.Path",\n          "search.config.get_model_slug",\n          "search.config.get_search_config"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "merkle\\\\snapshot_manager.py",\n      "lines": "15-24",\n      "kind": "method",\n      "score": 0.55,\n      "chunk_id": "merkle\\\\snapshot_manager.py:15-24:method:__init__",\n      "graph": {\n        "calls": [\n          "Path"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:02:11 - Handling POST message
16:02:11 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:11 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"class for code relationship analysis","k":2},"_meta":{"claudecode/toolUseId":"toolu_01PagKwaHRPHtXAPVApcWJdr"}},"jsonrpc":"2.0","id":39}'
16:02:11 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for code relationship analysis', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01PagKwaHRPHtXAPVApcWJdr'}}, jsonrpc='2.0', id=39)
16:02:11 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'class for code relationship analysis', 'k': 2}, '_meta': {'claudecode/toolUseId': 'toolu_01PagKwaHRPHtXAPVApcWJdr'}}, jsonrpc='2.0', id=39)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DE90A250>))
INFO:     ::1:51579 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:11 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE90BC90>
16:02:11 - Processing request of type CallToolRequest
16:02:11 - Dispatching request of type CallToolRequest
16:02:11 - [TOOL_CALL] search_code
16:02:11 - [SEARCH] query='class for code relationship analysis', k=2, mode='auto'
16:02:11 - [ROUTING] Query: 'class for code relationship analysis...' → bge_m3 (confidence: 0.04, reason: Low confidence (0.04 < 0.05) - using default (bge_m3))
16:02:11 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:11 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:02:11 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:02:11 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:11 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:11 - [INIT] BM25Index created successfully
16:02:11 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:02:11 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:11 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:11 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:02:11 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:02:12 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:02:12 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:02:12 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:02:12 - [INIT] Loaded existing dense index with 1445 vectors
16:02:12 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:12 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:12 - Attempting to populate HybridSearcher with existing dense index data
16:02:12 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:12 - Searcher initialized for project: claude-context-local
16:02:12 - [MULTI_HOP] Starting 2-hop search for 'class for code relationship analysis' (k=2, expansion=0.3, mode=semantic)
16:02:12 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:02:12 - Search mode: semantic, hybrid enabled: True
16:02:12 - Index manager search called with k=4, filters=None
16:02:12 - Index has 1445 total vectors
16:02:12 - [MULTI_HOP] Hop 1: Found 4 initial results (39.6ms)
16:02:12 - Index manager search called with k=2, filters=None
16:02:12 - Index has 1445 total vectors
16:02:12 - Index manager search called with k=2, filters=None
16:02:12 - Index has 1445 total vectors
16:02:12 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 6, 8.8ms)
16:02:12 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:02:12 - [MULTI_HOP] Complete: 2 results | Total=71ms (Hop1=40ms, Expansion=9ms, Rerank=23ms)
16:02:12 - Response sent
16:02:12 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=39, result={'content': [{'type': 'text', 'text': '{\n  "query": "class for code relationship analysis",\n  "results": [\n    {\n      "file": "mcp_server\\\\tools\\\\code_relationship_analyzer.py",\n      "lines": "74-94",\n      "kind": "method",\n      "score": 0.85,\n      "chunk_id": "mcp_server\\\\tools\\\\code_relationship_analyzer.py:74-94:method:__init__"\n    },\n    {\n      "file": "graph\\\\relationship_extractors\\\\base_extractor.py",\n      "lines": "43-77",\n      "kind": "decorated_definition",\n      "score": 0.78,\n      "chunk_id": "graph\\\\relationship_extractors\\\\base_extractor.py:43-77:decorated_definition:extract"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.03773584905660377,\n    "reason": "Low confidence (0.04 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 2 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:02:33 - Handling POST message
16:02:33 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:33 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"embeddings\\\\\\\\embedder.py:482-576:method:embed_chunks"},"_meta":{"claudecode/toolUseId":"toolu_01E1MjC9WQruGPfrwUA4FAR7"}},"jsonrpc":"2.0","id":40}'
16:02:33 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'embeddings\\\\embedder.py:482-576:method:embed_chunks'}, '_meta': {'claudecode/toolUseId': 'toolu_01E1MjC9WQruGPfrwUA4FAR7'}}, jsonrpc='2.0', id=40)
16:02:33 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'embeddings\\\\embedder.py:482-576:method:embed_chunks'}, '_meta': {'claudecode/toolUseId': 'toolu_01E1MjC9WQruGPfrwUA4FAR7'}}, jsonrpc='2.0', id=40)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000244516DBB90>))
INFO:     ::1:64048 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:33 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE90BD90>
16:02:33 - Processing request of type CallToolRequest
16:02:33 - Dispatching request of type CallToolRequest
16:02:33 - [TOOL_CALL] find_connections
16:02:33 - [FIND_CONNECTIONS] chunk_id=embeddings/embedder.py:482-576:method:embed_chunks, symbol_name=None, depth=3
16:02:33 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:33 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:33 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:33 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:33 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:33 - [INIT] BM25Index created successfully
16:02:33 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:33 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:33 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:33 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:33 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:34 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:34 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:34 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:34 - [INIT] Loaded existing dense index with 1445 vectors
16:02:34 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:34 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:34 - Attempting to populate HybridSearcher with existing dense index data
16:02:34 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:34 - Searcher initialized for project: claude-context-local
16:02:34 - Response sent
16:02:34 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=40, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "embeddings/embedder.py:482-576:method:embed_chunks",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\embeddings\\\\embedder.py",\n    "lines": "482-576",\n    "kind": "method",\n    "name": "embed_chunks"\n  },\n  "chunk_id": "embeddings/embedder.py:482-576:method:embed_chunks",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\embeddings\\\\embedder.py"\n  ],\n  "dependency_graph": {\n    "embeddings/embedder.py:482-576:method:embed_chunks": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "CodeChunk",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "EmbeddingResult",\n      "relationship_type": "uses_type",\n      "line": 3,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [\n    {\n      "target_name": "search.config.get_search_config",\n      "relationship_type": "imports",\n      "line": 9,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:34 - Handling POST message
16:02:34 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:34 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"search\\\\\\\\hybrid_searcher.py:57-1400:class:HybridSearcher"},"_meta":{"claudecode/toolUseId":"toolu_01X2PQX4sjWVuxYY2LpzSZHt"}},"jsonrpc":"2.0","id":41}'
16:02:34 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\hybrid_searcher.py:57-1400:class:HybridSearcher'}, '_meta': {'claudecode/toolUseId': 'toolu_01X2PQX4sjWVuxYY2LpzSZHt'}}, jsonrpc='2.0', id=41)
16:02:34 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\hybrid_searcher.py:57-1400:class:HybridSearcher'}, '_meta': {'claudecode/toolUseId': 'toolu_01X2PQX4sjWVuxYY2LpzSZHt'}}, jsonrpc='2.0', id=41)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x000002445187BD90>))
INFO:     ::1:64048 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:34 - Received message: <mcp.shared.session.RequestResponder object at 0x000002445173A750>
16:02:34 - Processing request of type CallToolRequest
16:02:34 - Dispatching request of type CallToolRequest
16:02:34 - [TOOL_CALL] find_connections
16:02:34 - [FIND_CONNECTIONS] chunk_id=search/hybrid_searcher.py:57-1400:class:HybridSearcher, symbol_name=None, depth=3
16:02:34 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:34 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:34 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:34 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:34 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:34 - [INIT] BM25Index created successfully
16:02:34 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:34 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:34 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:34 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:34 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:34 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:34 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:34 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:34 - [INIT] Loaded existing dense index with 1445 vectors
16:02:34 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:34 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:34 - Attempting to populate HybridSearcher with existing dense index data
16:02:34 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:34 - Searcher initialized for project: claude-context-local
16:02:34 - Response sent
16:02:34 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=41, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "search/hybrid_searcher.py:57-1400:class:HybridSearcher",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\hybrid_searcher.py",\n    "lines": "57-1400",\n    "kind": "class",\n    "name": "HybridSearcher"\n  },\n  "chunk_id": "search/hybrid_searcher.py:57-1400:class:HybridSearcher",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\hybrid_searcher.py"\n  ],\n  "dependency_graph": {\n    "search/hybrid_searcher.py:57-1400:class:HybridSearcher": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 1231,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "float",\n      "relationship_type": "uses_type",\n      "line": 909,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 1231,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "bool",\n      "relationship_type": "uses_type",\n      "line": 1060,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "SearchResult",\n      "relationship_type": "uses_type",\n      "line": 871,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "set",\n      "relationship_type": "uses_type",\n      "line": 1231,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [\n    {\n      "target_name": "numpy",\n      "relationship_type": "imports",\n      "line": 725,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "embeddings.embedder.EmbeddingResult",\n      "relationship_type": "imports",\n      "line": 283,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": ".config.get_search_config",\n      "relationship_type": "imports",\n      "line": 346,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": ".searcher.SearchResult",\n      "relationship_type": "imports",\n      "line": 495,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": ".config.SearchConfigManager",\n      "relationship_type": "imports",\n      "line": 581,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "pathlib.Path",\n      "relationship_type": "imports",\n      "line": 822,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "embeddings.embedder.CodeEmbedder",\n      "relationship_type": "imports",\n      "line": 824,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "traceback",\n      "relationship_type": "imports",\n      "line": 1283,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": ".reranker.SearchResult",\n      "relationship_type": "imports",\n      "line": 645,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:34 - Handling POST message
16:02:34 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:34 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"graph\\\\\\\\call_graph_extractor.py:93-126:method:extract_calls"},"_meta":{"claudecode/toolUseId":"toolu_01KvgXKts2zRyqjBf24Z7cWJ"}},"jsonrpc":"2.0","id":42}'
16:02:34 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'graph\\\\call_graph_extractor.py:93-126:method:extract_calls'}, '_meta': {'claudecode/toolUseId': 'toolu_01KvgXKts2zRyqjBf24Z7cWJ'}}, jsonrpc='2.0', id=42)
16:02:34 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'graph\\\\call_graph_extractor.py:93-126:method:extract_calls'}, '_meta': {'claudecode/toolUseId': 'toolu_01KvgXKts2zRyqjBf24Z7cWJ'}}, jsonrpc='2.0', id=42)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451DC0DD0>))
INFO:     ::1:64048 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:34 - Received message: <mcp.shared.session.RequestResponder object at 0x00000244527CE950>
16:02:34 - Processing request of type CallToolRequest
16:02:34 - Dispatching request of type CallToolRequest
16:02:34 - [TOOL_CALL] find_connections
16:02:34 - [FIND_CONNECTIONS] chunk_id=graph/call_graph_extractor.py:93-126:method:extract_calls, symbol_name=None, depth=3
16:02:34 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:34 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:34 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:34 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:34 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:34 - [INIT] BM25Index created successfully
16:02:34 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:35 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:35 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:35 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:35 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:35 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:35 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:35 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:35 - [INIT] Loaded existing dense index with 1445 vectors
16:02:35 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:35 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:35 - Attempting to populate HybridSearcher with existing dense index data
16:02:35 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:35 - Searcher initialized for project: claude-context-local
16:02:35 - Response sent
16:02:35 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=42, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "graph/call_graph_extractor.py:93-126:method:extract_calls",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\call_graph_extractor.py",\n    "lines": "93-126",\n    "kind": "method",\n    "name": "extract_calls"\n  },\n  "chunk_id": "graph/call_graph_extractor.py:93-126:method:extract_calls",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\call_graph_extractor.py"\n  ],\n  "dependency_graph": {\n    "graph/call_graph_extractor.py:93-126:method:extract_calls": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "CallEdge",\n      "relationship_type": "uses_type",\n      "line": 3,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:35 - Handling POST message
16:02:35 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:35 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"search\\\\\\\\indexer.py:218-259:method:_load_index"},"_meta":{"claudecode/toolUseId":"toolu_01MU5Vw8EHi41tz3abVCdhK4"}},"jsonrpc":"2.0","id":43}'
16:02:35 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\indexer.py:218-259:method:_load_index'}, '_meta': {'claudecode/toolUseId': 'toolu_01MU5Vw8EHi41tz3abVCdhK4'}}, jsonrpc='2.0', id=43)
16:02:35 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\indexer.py:218-259:method:_load_index'}, '_meta': {'claudecode/toolUseId': 'toolu_01MU5Vw8EHi41tz3abVCdhK4'}}, jsonrpc='2.0', id=43)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F10B7790>))
INFO:     ::1:64048 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:35 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F10B7D10>
16:02:35 - Processing request of type CallToolRequest
16:02:35 - Dispatching request of type CallToolRequest
16:02:35 - [TOOL_CALL] find_connections
16:02:35 - [FIND_CONNECTIONS] chunk_id=search/indexer.py:218-259:method:_load_index, symbol_name=None, depth=3
16:02:35 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:35 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:35 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:35 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:35 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:35 - [INIT] BM25Index created successfully
16:02:35 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:35 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:35 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:35 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:35 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:35 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:35 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:35 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:35 - [INIT] Loaded existing dense index with 1445 vectors
16:02:35 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:35 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:35 - Attempting to populate HybridSearcher with existing dense index data
16:02:35 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:35 - Searcher initialized for project: claude-context-local
16:02:35 - Response sent
16:02:35 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=43, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "search/indexer.py:218-259:method:_load_index",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\indexer.py",\n    "lines": "218-259",\n    "kind": "method",\n    "name": "_load_index"\n  },\n  "chunk_id": "search/indexer.py:218-259:method:_load_index",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\indexer.py"\n  ],\n  "dependency_graph": {\n    "search/indexer.py:218-259:method:_load_index": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:35 - Handling POST message
16:02:35 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:35 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"graph\\\\\\\\graph_storage.py:18-449:class:CodeGraphStorage"},"_meta":{"claudecode/toolUseId":"toolu_013g3JyBJ1dGfytMsy8Q3S1c"}},"jsonrpc":"2.0","id":44}'
16:02:35 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'graph\\\\graph_storage.py:18-449:class:CodeGraphStorage'}, '_meta': {'claudecode/toolUseId': 'toolu_013g3JyBJ1dGfytMsy8Q3S1c'}}, jsonrpc='2.0', id=44)
16:02:35 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'graph\\\\graph_storage.py:18-449:class:CodeGraphStorage'}, '_meta': {'claudecode/toolUseId': 'toolu_013g3JyBJ1dGfytMsy8Q3S1c'}}, jsonrpc='2.0', id=44)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451739F50>))
INFO:     ::1:64048 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:35 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F10B7250>
16:02:35 - Processing request of type CallToolRequest
16:02:35 - Dispatching request of type CallToolRequest
16:02:35 - [TOOL_CALL] find_connections
16:02:35 - [FIND_CONNECTIONS] chunk_id=graph/graph_storage.py:18-449:class:CodeGraphStorage, symbol_name=None, depth=3
16:02:35 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:35 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:35 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:35 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:35 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:35 - [INIT] BM25Index created successfully
16:02:35 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:36 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:36 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:36 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:36 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:36 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:36 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:36 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:36 - [INIT] Loaded existing dense index with 1445 vectors
16:02:36 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:36 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:36 - Attempting to populate HybridSearcher with existing dense index data
16:02:36 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:36 - Searcher initialized for project: claude-context-local
16:02:36 - Response sent
16:02:36 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=44, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "graph/graph_storage.py:18-449:class:CodeGraphStorage",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\graph_storage.py",\n    "lines": "18-449",\n    "kind": "class",\n    "name": "CodeGraphStorage"\n  },\n  "chunk_id": "graph/graph_storage.py:18-449:class:CodeGraphStorage",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\graph_storage.py"\n  ],\n  "dependency_graph": {\n    "graph/graph_storage.py:18-449:class:CodeGraphStorage": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 430,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "Path",\n      "relationship_type": "uses_type",\n      "line": 13,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 426,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "bool",\n      "relationship_type": "uses_type",\n      "line": 430,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "RelationshipEdge",\n      "relationship_type": "uses_type",\n      "line": 106,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [\n    {\n      "chunk_id": "graph/graph_queries.py:18-268:class:GraphQueryEngine",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\graph_queries.py",\n      "lines": "18-268",\n      "kind": "class",\n      "source_name": "GraphQueryEngine",\n      "relationship_type": "uses_type",\n      "line": 8,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "graph/graph_queries.py:25-39:method:__init__",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\graph_queries.py",\n      "lines": "25-39",\n      "kind": "method",\n      "source_name": "__init__",\n      "relationship_type": "uses_type",\n      "line": 1,\n      "confidence": 1.0\n    }\n  ],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:48 - Handling POST message
16:02:48 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:48 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"search\\\\\\\\query_router.py:24-306:class:QueryRouter"},"_meta":{"claudecode/toolUseId":"toolu_01QTG2VnsEaAoFWR3eoGDYzf"}},"jsonrpc":"2.0","id":45}'
16:02:48 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\query_router.py:24-306:class:QueryRouter'}, '_meta': {'claudecode/toolUseId': 'toolu_01QTG2VnsEaAoFWR3eoGDYzf'}}, jsonrpc='2.0', id=45)
16:02:48 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\query_router.py:24-306:class:QueryRouter'}, '_meta': {'claudecode/toolUseId': 'toolu_01QTG2VnsEaAoFWR3eoGDYzf'}}, jsonrpc='2.0', id=45)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DE4CD890>))
INFO:     ::1:58529 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:48 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F1F09990>
16:02:48 - Processing request of type CallToolRequest
16:02:48 - Dispatching request of type CallToolRequest
16:02:48 - [TOOL_CALL] find_connections
16:02:48 - [FIND_CONNECTIONS] chunk_id=search/query_router.py:24-306:class:QueryRouter, symbol_name=None, depth=3
16:02:48 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:48 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:48 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:48 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:48 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:48 - [INIT] BM25Index created successfully
16:02:48 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:48 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:48 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:48 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:48 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:48 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:48 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:48 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:48 - [INIT] Loaded existing dense index with 1445 vectors
16:02:48 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:48 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:48 - Attempting to populate HybridSearcher with existing dense index data
16:02:48 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:48 - Searcher initialized for project: claude-context-local
16:02:48 - Response sent
16:02:48 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=45, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "search/query_router.py:24-306:class:QueryRouter",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\query_router.py",\n    "lines": "24-306",\n    "kind": "class",\n    "name": "QueryRouter"\n  },\n  "chunk_id": "search/query_router.py:24-306:class:QueryRouter",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\query_router.py"\n  ],\n  "dependency_graph": {\n    "search/query_router.py:24-306:class:QueryRouter": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "bool",\n      "relationship_type": "uses_type",\n      "line": 165,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 277,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "float",\n      "relationship_type": "uses_type",\n      "line": 233,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "RoutingDecision",\n      "relationship_type": "uses_type",\n      "line": 175,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "list",\n      "relationship_type": "uses_type",\n      "line": 277,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:48 - Handling POST message
16:02:48 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:48 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"merkle\\\\\\\\snapshot_manager.py:12-346:class:SnapshotManager"},"_meta":{"claudecode/toolUseId":"toolu_014nkQRuD6j92NigAftsXBqd"}},"jsonrpc":"2.0","id":46}'
16:02:48 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'merkle\\\\snapshot_manager.py:12-346:class:SnapshotManager'}, '_meta': {'claudecode/toolUseId': 'toolu_014nkQRuD6j92NigAftsXBqd'}}, jsonrpc='2.0', id=46)
16:02:48 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'merkle\\\\snapshot_manager.py:12-346:class:SnapshotManager'}, '_meta': {'claudecode/toolUseId': 'toolu_014nkQRuD6j92NigAftsXBqd'}}, jsonrpc='2.0', id=46)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451FEECD0>))
INFO:     ::1:58529 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:48 - Received message: <mcp.shared.session.RequestResponder object at 0x00000244518EAFD0>
16:02:48 - Processing request of type CallToolRequest
16:02:48 - Dispatching request of type CallToolRequest
16:02:48 - [TOOL_CALL] find_connections
16:02:48 - [FIND_CONNECTIONS] chunk_id=merkle/snapshot_manager.py:12-346:class:SnapshotManager, symbol_name=None, depth=3
16:02:48 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:48 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:48 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:48 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:48 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:48 - [INIT] BM25Index created successfully
16:02:48 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:48 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:48 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:48 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:48 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:48 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:48 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:48 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:48 - [INIT] Loaded existing dense index with 1445 vectors
16:02:48 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:48 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:48 - Attempting to populate HybridSearcher with existing dense index data
16:02:48 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:48 - Searcher initialized for project: claude-context-local
16:02:48 - Response sent
16:02:48 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=46, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "merkle/snapshot_manager.py:12-346:class:SnapshotManager",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\merkle\\\\snapshot_manager.py",\n    "lines": "12-346",\n    "kind": "class",\n    "name": "SnapshotManager"\n  },\n  "chunk_id": "merkle/snapshot_manager.py:12-346:class:SnapshotManager",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\merkle\\\\snapshot_manager.py"\n  ],\n  "dependency_graph": {\n    "merkle/snapshot_manager.py:12-346:class:SnapshotManager": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "Path",\n      "relationship_type": "uses_type",\n      "line": 298,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 298,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 291,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "MerkleDAG",\n      "relationship_type": "uses_type",\n      "line": 163,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "bool",\n      "relationship_type": "uses_type",\n      "line": 214,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "float",\n      "relationship_type": "uses_type",\n      "line": 320,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [\n    {\n      "chunk_id": "search\\\\incremental_indexer.py:50-69:method:__init__",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\incremental_indexer.py",\n      "lines": "50-69",\n      "kind": "method",\n      "source_name": "__init__",\n      "relationship_type": "uses_type",\n      "line": 6,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "merkle/change_detector.py:45-253:class:ChangeDetector",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\merkle\\\\change_detector.py",\n      "lines": "45-253",\n      "kind": "class",\n      "source_name": "ChangeDetector",\n      "relationship_type": "uses_type",\n      "line": 4,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "merkle/change_detector.py:48-54:method:__init__",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\merkle\\\\change_detector.py",\n      "lines": "48-54",\n      "kind": "method",\n      "source_name": "__init__",\n      "relationship_type": "uses_type",\n      "line": 1,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "merkle\\\\change_detector.py:48-54:method:__init__",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\merkle\\\\change_detector.py",\n      "lines": "48-54",\n      "kind": "method",\n      "source_name": "__init__",\n      "relationship_type": "uses_type",\n      "line": 1,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "search/incremental_indexer.py:50-69:method:__init__",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\incremental_indexer.py",\n      "lines": "50-69",\n      "kind": "method",\n      "source_name": "__init__",\n      "relationship_type": "uses_type",\n      "line": 6,\n      "confidence": 1.0\n    },\n    {\n      "chunk_id": "search/incremental_indexer.py:47-624:class:IncrementalIndexer",\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\incremental_indexer.py",\n      "lines": "47-624",\n      "kind": "class",\n      "source_name": "IncrementalIndexer",\n      "relationship_type": "uses_type",\n      "line": 9,\n      "confidence": 1.0\n    }\n  ],\n  "imports": [\n    {\n      "target_name": "sys",\n      "relationship_type": "imports",\n      "line": 96,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "pathlib.Path",\n      "relationship_type": "imports",\n      "line": 97,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "search.config.get_model_slug",\n      "relationship_type": "imports",\n      "line": 116,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "search.config.get_search_config",\n      "relationship_type": "imports",\n      "line": 116,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:49 - Handling POST message
16:02:49 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:49 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"search\\\\\\\\bm25_index.py:315-360:method:search"},"_meta":{"claudecode/toolUseId":"toolu_012bKXqSkxannXgd4dXyLMU9"}},"jsonrpc":"2.0","id":47}'
16:02:49 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\bm25_index.py:315-360:method:search'}, '_meta': {'claudecode/toolUseId': 'toolu_012bKXqSkxannXgd4dXyLMU9'}}, jsonrpc='2.0', id=47)
16:02:49 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\bm25_index.py:315-360:method:search'}, '_meta': {'claudecode/toolUseId': 'toolu_012bKXqSkxannXgd4dXyLMU9'}}, jsonrpc='2.0', id=47)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BF0E5710>))
INFO:     ::1:58529 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:49 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F2E66C10>
16:02:49 - Processing request of type CallToolRequest
16:02:49 - Dispatching request of type CallToolRequest
16:02:49 - [TOOL_CALL] find_connections
16:02:49 - [FIND_CONNECTIONS] chunk_id=search/bm25_index.py:315-360:method:search, symbol_name=None, depth=3
16:02:49 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:49 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:49 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:49 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:49 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:49 - [INIT] BM25Index created successfully
16:02:49 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:49 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:49 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:49 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:49 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:49 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:49 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:49 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:49 - [INIT] Loaded existing dense index with 1445 vectors
16:02:49 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:49 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:49 - Attempting to populate HybridSearcher with existing dense index data
16:02:49 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:49 - Searcher initialized for project: claude-context-local
16:02:49 - Response sent
16:02:49 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=47, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "search/bm25_index.py:315-360:method:search",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\bm25_index.py",\n    "lines": "315-360",\n    "kind": "method",\n    "name": "search"\n  },\n  "chunk_id": "search/bm25_index.py:315-360:method:search",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\bm25_index.py"\n  ],\n  "dependency_graph": {\n    "search/bm25_index.py:315-360:method:search": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 3,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "float",\n      "relationship_type": "uses_type",\n      "line": 3,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:49 - Handling POST message
16:02:49 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:49 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"search\\\\\\\\reranker.py:20-311:class:RRFReranker"},"_meta":{"claudecode/toolUseId":"toolu_014eXcDCa3vBqMnwaJA26iob"}},"jsonrpc":"2.0","id":48}'
16:02:49 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\reranker.py:20-311:class:RRFReranker'}, '_meta': {'claudecode/toolUseId': 'toolu_014eXcDCa3vBqMnwaJA26iob'}}, jsonrpc='2.0', id=48)
16:02:49 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'search\\\\reranker.py:20-311:class:RRFReranker'}, '_meta': {'claudecode/toolUseId': 'toolu_014eXcDCa3vBqMnwaJA26iob'}}, jsonrpc='2.0', id=48)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DE059A90>))
INFO:     ::1:58529 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:49 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F2E65390>
16:02:49 - Processing request of type CallToolRequest
16:02:49 - Dispatching request of type CallToolRequest
16:02:49 - [TOOL_CALL] find_connections
16:02:49 - [FIND_CONNECTIONS] chunk_id=search/reranker.py:20-311:class:RRFReranker, symbol_name=None, depth=3
16:02:49 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:49 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:49 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:49 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:49 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:49 - [INIT] BM25Index created successfully
16:02:49 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:49 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:49 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:49 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:49 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:49 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:49 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:49 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:49 - [INIT] Loaded existing dense index with 1445 vectors
16:02:49 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:49 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:49 - Attempting to populate HybridSearcher with existing dense index data
16:02:49 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:49 - Searcher initialized for project: claude-context-local
16:02:49 - Response sent
16:02:49 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=48, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "search/reranker.py:20-311:class:RRFReranker",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\reranker.py",\n    "lines": "20-311",\n    "kind": "class",\n    "name": "RRFReranker"\n  },\n  "chunk_id": "search/reranker.py:20-311:class:RRFReranker",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\search\\\\reranker.py"\n  ],\n  "dependency_graph": {\n    "search/reranker.py:20-311:class:RRFReranker": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "int",\n      "relationship_type": "uses_type",\n      "line": 59,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "float",\n      "relationship_type": "uses_type",\n      "line": 57,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "SearchResult",\n      "relationship_type": "uses_type",\n      "line": 58,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 59,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:02:50 - Handling POST message
16:02:50 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:02:50 - Received JSON: b'{"method":"tools/call","params":{"name":"find_connections","arguments":{"chunk_id":"chunking\\\\\\\\multi_language_chunker.py:231-410:method:_convert_tree_chunks"},"_meta":{"claudecode/toolUseId":"toolu_01EBQDfBhrd4NMqFUQ9Ns5FW"}},"jsonrpc":"2.0","id":49}'
16:02:50 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'chunking\\\\multi_language_chunker.py:231-410:method:_convert_tree_chunks'}, '_meta': {'claudecode/toolUseId': 'toolu_01EBQDfBhrd4NMqFUQ9Ns5FW'}}, jsonrpc='2.0', id=49)
16:02:50 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_connections', 'arguments': {'chunk_id': 'chunking\\\\multi_language_chunker.py:231-410:method:_convert_tree_chunks'}, '_meta': {'claudecode/toolUseId': 'toolu_01EBQDfBhrd4NMqFUQ9Ns5FW'}}, jsonrpc='2.0', id=49)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DF20E950>))
INFO:     ::1:58529 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:02:50 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE0590D0>
16:02:50 - Processing request of type CallToolRequest
16:02:50 - Dispatching request of type CallToolRequest
16:02:50 - [TOOL_CALL] find_connections
16:02:50 - [FIND_CONNECTIONS] chunk_id=chunking/multi_language_chunker.py:231-410:method:_convert_tree_chunks, symbol_name=None, depth=3
16:02:50 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:02:50 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:02:50 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:02:50 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:50 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:02:50 - [INIT] BM25Index created successfully
16:02:50 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:02:50 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:02:50 - [INIT] Loaded existing BM25 index with 1445 documents
16:02:50 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:02:50 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:02:50 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:02:50 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:02:50 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:02:50 - [INIT] Loaded existing dense index with 1445 vectors
16:02:50 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:02:50 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:02:50 - Attempting to populate HybridSearcher with existing dense index data
16:02:50 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:02:50 - Searcher initialized for project: claude-context-local
16:02:50 - Response sent
16:02:50 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=49, result={'content': [{'type': 'text', 'text': '{\n  "symbol": {\n    "chunk_id": "chunking/multi_language_chunker.py:231-410:method:_convert_tree_chunks",\n    "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\chunking\\\\multi_language_chunker.py",\n    "lines": "231-410",\n    "kind": "method",\n    "name": "_convert_tree_chunks"\n  },\n  "chunk_id": "chunking/multi_language_chunker.py:231-410:method:_convert_tree_chunks",\n  "direct_callers": [],\n  "indirect_callers": [],\n  "similar_code": [],\n  "total_impacted": 0,\n  "file_count": 1,\n  "affected_files": [\n    "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\chunking\\\\multi_language_chunker.py"\n  ],\n  "dependency_graph": {\n    "chunking/multi_language_chunker.py:231-410:method:_convert_tree_chunks": []\n  },\n  "parent_classes": [],\n  "child_classes": [],\n  "uses_types": [\n    {\n      "target_name": "TreeSitterChunk",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "str",\n      "relationship_type": "uses_type",\n      "line": 2,\n      "confidence": 1.0,\n      "metadata": {}\n    },\n    {\n      "target_name": "CodeChunk",\n      "relationship_type": "uses_type",\n      "line": 3,\n      "confidence": 1.0,\n      "metadata": {}\n    }\n  ],\n  "used_as_type_in": [],\n  "imports": [],\n  "imported_by": [],\n  "system_message": "No connections found. This appears to be unused or entry-point code."\n}'}], 'isError': False})), metadata=None)
16:03:17 - Handling POST message
16:03:17 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:17 - Received JSON: b'{"method":"tools/call","params":{"name":"find_similar_code","arguments":{"chunk_id":"search\\\\\\\\hybrid_searcher.py:850-867:method:_search_bm25","k":3},"_meta":{"claudecode/toolUseId":"toolu_01GP54Zva6L3J4BXxjUaPjUD"}},"jsonrpc":"2.0","id":50}'
16:03:17 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'search\\\\hybrid_searcher.py:850-867:method:_search_bm25', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01GP54Zva6L3J4BXxjUaPjUD'}}, jsonrpc='2.0', id=50)
16:03:17 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'search\\\\hybrid_searcher.py:850-867:method:_search_bm25', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01GP54Zva6L3J4BXxjUaPjUD'}}, jsonrpc='2.0', id=50)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BF864ED0>))
INFO:     ::1:52969 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:17 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F01F3110>
16:03:17 - Processing request of type CallToolRequest
16:03:17 - Dispatching request of type CallToolRequest
16:03:17 - [TOOL_CALL] find_similar_code
16:03:17 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:17 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:17 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:17 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:17 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:17 - [INIT] BM25Index created successfully
16:03:17 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:17 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:17 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:17 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:17 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:17 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:17 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:17 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:17 - [INIT] Loaded existing dense index with 1445 vectors
16:03:17 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:17 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:17 - Attempting to populate HybridSearcher with existing dense index data
16:03:17 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:17 - Searcher initialized for project: claude-context-local
16:03:17 - Response sent
16:03:17 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=50, result={'content': [{'type': 'text', 'text': '{\n  "reference_chunk": "search/hybrid_searcher.py:850-867:method:_search_bm25",\n  "similar_chunks": [],\n  "count": 0\n}'}], 'isError': False})), metadata=None)
16:03:18 - Handling POST message
16:03:18 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:18 - Received JSON: b'{"method":"tools/call","params":{"name":"find_similar_code","arguments":{"chunk_id":"graph\\\\\\\\relationship_extractors\\\\\\\\inheritance_extractor.py:20-283:class:InheritanceExtractor","k":3},"_meta":{"claudecode/toolUseId":"toolu_01VJUfhuU7omiDhue2q7RMCS"}},"jsonrpc":"2.0","id":51}'
16:03:18 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'graph\\\\relationship_extractors\\\\inheritance_extractor.py:20-283:class:InheritanceExtractor', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01VJUfhuU7omiDhue2q7RMCS'}}, jsonrpc='2.0', id=51)
16:03:18 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'graph\\\\relationship_extractors\\\\inheritance_extractor.py:20-283:class:InheritanceExtractor', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01VJUfhuU7omiDhue2q7RMCS'}}, jsonrpc='2.0', id=51)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F21C6D50>))
INFO:     ::1:52969 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:18 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BF921E10>
16:03:18 - Processing request of type CallToolRequest
16:03:18 - Dispatching request of type CallToolRequest
16:03:18 - [TOOL_CALL] find_similar_code
16:03:18 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:18 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:18 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:18 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:18 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:18 - [INIT] BM25Index created successfully
16:03:18 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:18 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:18 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:18 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:18 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:18 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:18 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:18 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:18 - [INIT] Loaded existing dense index with 1445 vectors
16:03:18 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:18 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:18 - Attempting to populate HybridSearcher with existing dense index data
16:03:18 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:18 - Searcher initialized for project: claude-context-local
16:03:18 - Response sent
16:03:18 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=51, result={'content': [{'type': 'text', 'text': '{\n  "reference_chunk": "graph/relationship_extractors/inheritance_extractor.py:20-283:class:InheritanceExtractor",\n  "similar_chunks": [],\n  "count": 0\n}'}], 'isError': False})), metadata=None)
16:03:18 - Handling POST message
16:03:18 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:18 - Received JSON: b'{"method":"tools/call","params":{"name":"find_similar_code","arguments":{"chunk_id":"mcp_server\\\\\\\\tool_handlers.py:446-482:function:handle_find_similar_code","k":3},"_meta":{"claudecode/toolUseId":"toolu_01DvqR8p2Ta4ENFDNAbBq1wu"}},"jsonrpc":"2.0","id":52}'
16:03:18 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'mcp_server\\\\tool_handlers.py:446-482:function:handle_find_similar_code', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01DvqR8p2Ta4ENFDNAbBq1wu'}}, jsonrpc='2.0', id=52)
16:03:18 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'mcp_server\\\\tool_handlers.py:446-482:function:handle_find_similar_code', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01DvqR8p2Ta4ENFDNAbBq1wu'}}, jsonrpc='2.0', id=52)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DE007D10>))
INFO:     ::1:52969 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:18 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F21C4CD0>
16:03:18 - Processing request of type CallToolRequest
16:03:18 - Dispatching request of type CallToolRequest
16:03:18 - [TOOL_CALL] find_similar_code
16:03:18 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:18 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:18 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:18 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:18 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:18 - [INIT] BM25Index created successfully
16:03:18 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:19 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:19 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:19 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:19 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:19 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:19 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:19 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:19 - [INIT] Loaded existing dense index with 1445 vectors
16:03:19 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:19 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:19 - Attempting to populate HybridSearcher with existing dense index data
16:03:19 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:19 - Searcher initialized for project: claude-context-local
16:03:19 - Response sent
16:03:19 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=52, result={'content': [{'type': 'text', 'text': '{\n  "reference_chunk": "mcp_server/tool_handlers.py:446-482:function:handle_find_similar_code",\n  "similar_chunks": [],\n  "count": 0\n}'}], 'isError': False})), metadata=None)
16:03:19 - Handling POST message
16:03:19 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:19 - Received JSON: b'{"method":"tools/call","params":{"name":"find_similar_code","arguments":{"chunk_id":"tests\\\\\\\\unit\\\\\\\\test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters","k":3},"_meta":{"claudecode/toolUseId":"toolu_018XoWqKAHx4S4Lv2Emr9oWL"}},"jsonrpc":"2.0","id":53}'
16:03:19 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'tests\\\\unit\\\\test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_018XoWqKAHx4S4Lv2Emr9oWL'}}, jsonrpc='2.0', id=53)
16:03:19 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'tests\\\\unit\\\\test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_018XoWqKAHx4S4Lv2Emr9oWL'}}, jsonrpc='2.0', id=53)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EF8A8690>))
INFO:     ::1:52969 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:19 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BF953AD0>
16:03:19 - Processing request of type CallToolRequest
16:03:19 - Dispatching request of type CallToolRequest
16:03:19 - [TOOL_CALL] find_similar_code
16:03:19 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:19 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:19 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:19 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:19 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:19 - [INIT] BM25Index created successfully
16:03:19 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:19 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:19 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:19 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:19 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:19 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:19 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:19 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:19 - [INIT] Loaded existing dense index with 1445 vectors
16:03:19 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:19 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:19 - Attempting to populate HybridSearcher with existing dense index data
16:03:19 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:19 - Searcher initialized for project: claude-context-local
16:03:19 - Response sent
16:03:19 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=53, result={'content': [{'type': 'text', 'text': '{\n  "reference_chunk": "tests/unit/test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters",\n  "similar_chunks": [],\n  "count": 0\n}'}], 'isError': False})), metadata=None)
16:03:19 - Handling POST message
16:03:19 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:19 - Received JSON: b'{"method":"tools/call","params":{"name":"find_similar_code","arguments":{"chunk_id":"search\\\\\\\\incremental_indexer.py:50-69:method:__init__","k":3},"_meta":{"claudecode/toolUseId":"toolu_01TFVjFLJXKrXzWan9a7Zbv7"}},"jsonrpc":"2.0","id":54}'
16:03:19 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'search\\\\incremental_indexer.py:50-69:method:__init__', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01TFVjFLJXKrXzWan9a7Zbv7'}}, jsonrpc='2.0', id=54)
16:03:19 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'find_similar_code', 'arguments': {'chunk_id': 'search\\\\incremental_indexer.py:50-69:method:__init__', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01TFVjFLJXKrXzWan9a7Zbv7'}}, jsonrpc='2.0', id=54)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BFBEF650>))
INFO:     ::1:52969 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:19 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BFBECF90>
16:03:19 - Processing request of type CallToolRequest
16:03:19 - Dispatching request of type CallToolRequest
16:03:19 - [TOOL_CALL] find_similar_code
16:03:19 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:19 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:19 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:19 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:19 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:19 - [INIT] BM25Index created successfully
16:03:19 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:20 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:20 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:20 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:20 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:20 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:20 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:20 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:20 - [INIT] Loaded existing dense index with 1445 vectors
16:03:20 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:20 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:20 - Attempting to populate HybridSearcher with existing dense index data
16:03:20 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:20 - Searcher initialized for project: claude-context-local
16:03:20 - Response sent
16:03:20 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=54, result={'content': [{'type': 'text', 'text': '{\n  "reference_chunk": "search/incremental_indexer.py:50-69:method:__init__",\n  "similar_chunks": [],\n  "count": 0\n}'}], 'isError': False})), metadata=None)
16:03:39 - Handling POST message
16:03:39 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:39 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"chunk_id":"graph\\\\\\\\call_graph_extractor.py:93-126:method:extract_calls"},"_meta":{"claudecode/toolUseId":"toolu_017dkDehEFeZoFEC6eJc1JZV"}},"jsonrpc":"2.0","id":55}'
16:03:39 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'chunk_id': 'graph\\\\call_graph_extractor.py:93-126:method:extract_calls'}, '_meta': {'claudecode/toolUseId': 'toolu_017dkDehEFeZoFEC6eJc1JZV'}}, jsonrpc='2.0', id=55)
16:03:39 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'chunk_id': 'graph\\\\call_graph_extractor.py:93-126:method:extract_calls'}, '_meta': {'claudecode/toolUseId': 'toolu_017dkDehEFeZoFEC6eJc1JZV'}}, jsonrpc='2.0', id=55)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x0000024451DE4710>))
INFO:     ::1:50204 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:39 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE7C2D50>
16:03:39 - Processing request of type CallToolRequest
16:03:39 - Dispatching request of type CallToolRequest
16:03:39 - [TOOL_CALL] search_code
16:03:39 - [DIRECT_LOOKUP] chunk_id='graph\\call_graph_extractor.py:93-126:method:extract_calls'
16:03:39 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:39 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
16:03:39 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:39 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:39 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:39 - [INIT] BM25Index created successfully
16:03:39 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:40 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:40 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:40 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:40 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:40 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:40 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:40 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:40 - [INIT] Loaded existing dense index with 1445 vectors
16:03:40 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:40 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:40 - Attempting to populate HybridSearcher with existing dense index data
16:03:40 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:40 - Searcher initialized for project: claude-context-local
16:03:40 - Response sent
16:03:40 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=55, result={'content': [{'type': 'text', 'text': '{\n  "query": null,\n  "chunk_id": "graph\\\\\\\\call_graph_extractor.py:93-126:method:extract_calls",\n  "results": [\n    {\n      "file": "F:\\\\RD_PROJECTS\\\\COMPONENTS\\\\claude-context-local\\\\graph\\\\call_graph_extractor.py",\n      "lines": "93-126",\n      "kind": "method",\n      "score": 1.0,\n      "chunk_id": "graph\\\\\\\\call_graph_extractor.py:93-126:method:extract_calls"\n    }\n  ],\n  "routing": null,\n  "system_message": "Direct lookup successful. Use related chunk_ids for navigation."\n}'}], 'isError': False})), metadata=None)
16:03:40 - Handling POST message
16:03:40 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:40 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"search","file_pattern":"search","k":3},"_meta":{"claudecode/toolUseId":"toolu_01N6WmdvaaTWNrbjoSGrGAif"}},"jsonrpc":"2.0","id":56}'
16:03:40 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search', 'file_pattern': 'search', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01N6WmdvaaTWNrbjoSGrGAif'}}, jsonrpc='2.0', id=56)
16:03:40 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search', 'file_pattern': 'search', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01N6WmdvaaTWNrbjoSGrGAif'}}, jsonrpc='2.0', id=56)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F2073150>))
INFO:     ::1:50204 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:40 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243DE7C3850>
16:03:40 - Processing request of type CallToolRequest
16:03:40 - Dispatching request of type CallToolRequest
16:03:40 - [TOOL_CALL] search_code
16:03:40 - [SEARCH] query='search', k=3, mode='auto'
16:03:40 - [ROUTING] Query: 'search...' → bge_m3 (confidence: 0.02, reason: Low confidence (0.02 < 0.05) - using default (bge_m3))
16:03:40 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:40 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:40 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:40 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:40 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:40 - [INIT] BM25Index created successfully
16:03:40 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:40 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:40 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:40 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:40 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:40 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:40 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:40 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:40 - [INIT] Loaded existing dense index with 1445 vectors
16:03:40 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:40 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:40 - Attempting to populate HybridSearcher with existing dense index data
16:03:40 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:40 - Searcher initialized for project: claude-context-local
16:03:40 - [MULTI_HOP] Starting 2-hop search for 'search' (k=3, expansion=0.3, mode=semantic)
16:03:40 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:40 - Search mode: semantic, hybrid enabled: True
16:03:40 - Index manager search called with k=6, filters={'file_pattern': ['search']}
16:03:40 - Index has 1445 total vectors
16:03:40 - [MULTI_HOP] Hop 1: Found 6 initial results (33.6ms)
16:03:40 - Index manager search called with k=2, filters=None
16:03:40 - Index has 1445 total vectors
16:03:40 - Index manager search called with k=2, filters=None
16:03:40 - Index has 1445 total vectors
16:03:40 - Index manager search called with k=2, filters=None
16:03:40 - Index has 1445 total vectors
16:03:40 - [MULTI_HOP] Hop 2: Discovered 3 new chunks (total: 9, 0.0ms)
16:03:40 - [MULTI_HOP] Re-ranking 9 total chunks by query relevance
16:03:40 - [MULTI_HOP] Complete: 3 results | Total=97ms (Hop1=34ms, Expansion=0ms, Rerank=64ms)
16:03:40 - Response sent
16:03:40 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=56, result={'content': [{'type': 'text', 'text': '{\n  "query": "search",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_hybrid_search.py",\n      "lines": "239-271",\n      "kind": "decorated_definition",\n      "score": 0.78,\n      "chunk_id": "tests\\\\unit\\\\test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters"\n    },\n    {\n      "file": "tools\\\\search_helper.py",\n      "lines": "151-179",\n      "kind": "method",\n      "score": 0.77,\n      "chunk_id": "tools\\\\search_helper.py:151-179:method:show_help"\n    },\n    {\n      "file": "scripts\\\\__init__.py",\n      "lines": "1-2",\n      "kind": "module",\n      "score": 0.76,\n      "chunk_id": "scripts\\\\__init__.py:1-2:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.018867924528301886,\n    "reason": "Low confidence (0.02 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.018867924528301886,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. "\n}'}], 'isError': False})), metadata=None)
16:03:41 - Handling POST message
16:03:41 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:41 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"index","chunk_type":"class","k":3},"_meta":{"claudecode/toolUseId":"toolu_01FaqwkpmBGEJhxvqxAC5Jek"}},"jsonrpc":"2.0","id":57}'
16:03:41 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'index', 'chunk_type': 'class', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01FaqwkpmBGEJhxvqxAC5Jek'}}, jsonrpc='2.0', id=57)
16:03:41 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'index', 'chunk_type': 'class', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01FaqwkpmBGEJhxvqxAC5Jek'}}, jsonrpc='2.0', id=57)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243EFD69350>))
INFO:     ::1:50204 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:41 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F2070350>
16:03:41 - Processing request of type CallToolRequest
16:03:41 - Dispatching request of type CallToolRequest
16:03:41 - [TOOL_CALL] search_code
16:03:41 - [SEARCH] query='index', k=3, mode='auto'
16:03:41 - [ROUTING] Query: 'index...' → bge_m3 (confidence: 0.03, reason: Low confidence (0.03 < 0.05) - using default (bge_m3))
16:03:41 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:41 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:41 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:41 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:41 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:41 - [INIT] BM25Index created successfully
16:03:41 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:41 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:41 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:41 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:41 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:41 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:41 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:41 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:41 - [INIT] Loaded existing dense index with 1445 vectors
16:03:41 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:41 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:41 - Attempting to populate HybridSearcher with existing dense index data
16:03:41 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:41 - Searcher initialized for project: claude-context-local
16:03:41 - [MULTI_HOP] Starting 2-hop search for 'index' (k=3, expansion=0.3, mode=semantic)
16:03:41 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:41 - Search mode: semantic, hybrid enabled: True
16:03:41 - Index manager search called with k=6, filters={'chunk_type': 'class'}
16:03:41 - Index has 1445 total vectors
16:03:41 - [MULTI_HOP] Hop 1: Found 2 initial results (43.5ms)
16:03:41 - Index manager search called with k=2, filters=None
16:03:41 - Index has 1445 total vectors
16:03:41 - Index manager search called with k=2, filters=None
16:03:41 - Index has 1445 total vectors
16:03:41 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 4, 4.7ms)
16:03:41 - [MULTI_HOP] Re-ranking 4 total chunks by query relevance
16:03:41 - [MULTI_HOP] Complete: 3 results | Total=66ms (Hop1=44ms, Expansion=5ms, Rerank=17ms)
16:03:41 - Response sent
16:03:41 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=57, result={'content': [{'type': 'text', 'text': '{\n  "query": "index",\n  "results": [\n    {\n      "file": "search\\\\incremental_indexer.py",\n      "lines": "50-69",\n      "kind": "method",\n      "score": 0.9,\n      "chunk_id": "search\\\\incremental_indexer.py:50-69:method:__init__",\n      "graph": {\n        "calls": [\n          "Indexer",\n          "CodeEmbedder",\n          "MultiLanguageChunker",\n          "SnapshotManager"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_incremental_indexer.py",\n      "lines": "79-802",\n      "kind": "class",\n      "score": 0.86,\n      "chunk_id": "tests\\\\unit\\\\test_incremental_indexer.py:79-802:class:TestIncrementalIndexer",\n      "graph": {\n        "calls": [\n          "shutil"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\incremental_indexer.py",\n      "lines": "47-624",\n      "kind": "class",\n      "score": 0.6,\n      "chunk_id": "search\\\\incremental_indexer.py:47-624:class:IncrementalIndexer",\n      "graph": {\n        "calls": [\n          "Indexer",\n          "CodeEmbedder",\n          "MultiLanguageChunker",\n          "SnapshotManager",\n          "str",\n          "FileChanges",\n          "MerkleDAG",\n          "bool",\n          "IncrementalIndexResult",\n          "float",\n          "int",\n          "chunking.multi_language_chunker.MultiLanguageChunker",\n          "time",\n          "gc",\n          "torch",\n          "traceback"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.027777777777777776,\n    "reason": "Low confidence (0.03 < 0.05) - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.027777777777777776\n    }\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:41 - Handling POST message
16:03:41 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:41 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"parse","chunk_type":"function","k":3},"_meta":{"claudecode/toolUseId":"toolu_01KePvnoCfPXXB1D34fKf96h"}},"jsonrpc":"2.0","id":58}'
16:03:41 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'parse', 'chunk_type': 'function', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01KePvnoCfPXXB1D34fKf96h'}}, jsonrpc='2.0', id=58)
16:03:41 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'parse', 'chunk_type': 'function', 'k': 3}, '_meta': {'claudecode/toolUseId': 'toolu_01KePvnoCfPXXB1D34fKf96h'}}, jsonrpc='2.0', id=58)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000242BFB476D0>))
INFO:     ::1:50204 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:41 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F12CBCD0>
16:03:41 - Processing request of type CallToolRequest
16:03:41 - Dispatching request of type CallToolRequest
16:03:41 - [TOOL_CALL] search_code
16:03:41 - [SEARCH] query='parse', k=3, mode='auto'
16:03:41 - [ROUTING] Query: 'parse...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:03:41 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:41 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:41 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:41 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:41 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:41 - [INIT] BM25Index created successfully
16:03:41 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:41 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:41 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:41 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:41 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:41 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:41 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:41 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:41 - [INIT] Loaded existing dense index with 1445 vectors
16:03:41 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:41 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:41 - Attempting to populate HybridSearcher with existing dense index data
16:03:41 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:41 - Searcher initialized for project: claude-context-local
16:03:41 - [MULTI_HOP] Starting 2-hop search for 'parse' (k=3, expansion=0.3, mode=semantic)
16:03:41 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:41 - Search mode: semantic, hybrid enabled: True
16:03:41 - Index manager search called with k=6, filters={'chunk_type': 'function'}
16:03:41 - Index has 1445 total vectors
16:03:41 - [MULTI_HOP] Hop 1: Found 6 initial results (37.4ms)
16:03:41 - Index manager search called with k=2, filters=None
16:03:41 - Index has 1445 total vectors
16:03:41 - Index manager search called with k=2, filters=None
16:03:41 - Index has 1445 total vectors
16:03:41 - Index manager search called with k=2, filters=None
16:03:41 - Index has 1445 total vectors
16:03:41 - [MULTI_HOP] Hop 2: Discovered 1 new chunks (total: 7, 4.3ms)
16:03:41 - [MULTI_HOP] Re-ranking 7 total chunks by query relevance
16:03:41 - [MULTI_HOP] Complete: 3 results | Total=74ms (Hop1=37ms, Expansion=4ms, Rerank=31ms)
16:03:41 - Response sent
16:03:41 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=58, result={'content': [{'type': 'text', 'text': '{\n  "query": "parse",\n  "results": [\n    {\n      "file": "tests\\\\benchmarks\\\\capture_baseline.py",\n      "lines": "31-316",\n      "kind": "class",\n      "score": 0.83,\n      "chunk_id": "tests\\\\benchmarks\\\\capture_baseline.py:31-316:class:BaselineMetricsCapture",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "traceback"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\benchmarks\\\\capture_baseline.py",\n      "lines": "319-365",\n      "kind": "function",\n      "score": 0.56,\n      "chunk_id": "tests\\\\benchmarks\\\\capture_baseline.py:319-365:function:main",\n      "graph": {\n        "calls": [\n          "traceback"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tools\\\\batch_index.py",\n      "lines": "21-174",\n      "kind": "function",\n      "score": 0.55,\n      "chunk_id": "tools\\\\batch_index.py:21-174:function:main",\n      "graph": {\n        "calls": [\n          "traceback"\n        ],\n        "called_by": []\n      }\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:42 - Handling POST message
16:03:42 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:42 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"test","k":10},"_meta":{"claudecode/toolUseId":"toolu_016wAbtnrrj92ZAbhcWR1j4L"}},"jsonrpc":"2.0","id":59}'
16:03:42 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'test', 'k': 10}, '_meta': {'claudecode/toolUseId': 'toolu_016wAbtnrrj92ZAbhcWR1j4L'}}, jsonrpc='2.0', id=59)
16:03:42 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'test', 'k': 10}, '_meta': {'claudecode/toolUseId': 'toolu_016wAbtnrrj92ZAbhcWR1j4L'}}, jsonrpc='2.0', id=59)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F1DB1690>))
INFO:     ::1:50204 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:42 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F1DB3610>
16:03:42 - Processing request of type CallToolRequest
16:03:42 - Dispatching request of type CallToolRequest
16:03:42 - [TOOL_CALL] search_code
16:03:42 - [SEARCH] query='test', k=10, mode='auto'
16:03:42 - [ROUTING] Query: 'test...' → bge_m3 (confidence: 0.00, reason: No specific keywords matched - using default (bge_m3))
16:03:42 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:42 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:42 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:42 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:42 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:42 - [INIT] BM25Index created successfully
16:03:42 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:42 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:42 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:42 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:42 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:42 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:42 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:42 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:42 - [INIT] Loaded existing dense index with 1445 vectors
16:03:42 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:42 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:42 - Attempting to populate HybridSearcher with existing dense index data
16:03:42 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:42 - Searcher initialized for project: claude-context-local
16:03:42 - [MULTI_HOP] Starting 2-hop search for 'test' (k=10, expansion=0.3, mode=semantic)
16:03:42 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:42 - Search mode: semantic, hybrid enabled: True
16:03:42 - Index manager search called with k=20, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - [MULTI_HOP] Hop 1: Found 20 initial results (32.0ms)
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - Index manager search called with k=4, filters=None
16:03:42 - Index has 1445 total vectors
16:03:42 - [MULTI_HOP] Hop 2: Discovered 19 new chunks (total: 39, 30.3ms)
16:03:42 - [MULTI_HOP] Re-ranking 39 total chunks by query relevance
16:03:42 - [MULTI_HOP] Complete: 10 results | Total=112ms (Hop1=32ms, Expansion=30ms, Rerank=50ms)
16:03:42 - Response sent
16:03:42 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=59, result={'content': [{'type': 'text', 'text': '{\n  "query": "test",\n  "results": [\n    {\n      "file": "tests\\\\integration\\\\test_stemming_integration.py",\n      "lines": "136-166",\n      "kind": "decorated_definition",\n      "score": 0.86,\n      "chunk_id": "tests\\\\integration\\\\test_stemming_integration.py:136-166:decorated_definition:test_end_to_end_indexing_with_stemming"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_stemming_integration.py",\n      "lines": "392-449",\n      "kind": "decorated_definition",\n      "score": 0.85,\n      "chunk_id": "tests\\\\integration\\\\test_stemming_integration.py:392-449:decorated_definition:test_incremental_reindex_preserves_stemming"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_hybrid_search_integration.py",\n      "lines": "591-617",\n      "kind": "method",\n      "score": 0.85,\n      "chunk_id": "tests\\\\integration\\\\test_hybrid_search_integration.py:591-617:method:test_hybrid_searcher_uses_config"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_hybrid_search_integration.py",\n      "lines": "567-589",\n      "kind": "method",\n      "score": 0.83,\n      "chunk_id": "tests\\\\integration\\\\test_hybrid_search_integration.py:567-589:method:test_config_file_loading"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_installation.py",\n      "lines": "387-397",\n      "kind": "method",\n      "score": 0.82,\n      "chunk_id": "tests\\\\integration\\\\test_installation.py:387-397:method:test_pytorch_verification_cuda"\n    },\n    {\n      "file": "search\\\\bm25_index.py",\n      "lines": "40-158",\n      "kind": "class",\n      "score": 0.81,\n      "chunk_id": "search\\\\bm25_index.py:40-158:class:TextPreprocessor",\n      "graph": {\n        "calls": [\n          "bool",\n          "str"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_bm25_index.py",\n      "lines": "14-21",\n      "kind": "method",\n      "score": 0.81,\n      "chunk_id": "tests\\\\unit\\\\test_bm25_index.py:14-21:method:test_basic_tokenization"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_installation_flow.py",\n      "lines": "255-269",\n      "kind": "method",\n      "score": 0.81,\n      "chunk_id": "tests\\\\integration\\\\test_installation_flow.py:255-269:method:test_pytorch_installation_validation"\n    },\n    {\n      "file": "tests\\\\unit\\\\test_bm25_index.py",\n      "lines": "92-108",\n      "kind": "method",\n      "score": 0.81,\n      "chunk_id": "tests\\\\unit\\\\test_bm25_index.py:92-108:method:test_stemming_verb_forms"\n    },\n    {\n      "file": "tests\\\\integration\\\\test_installation_flow.py",\n      "lines": "239-344",\n      "kind": "class",\n      "score": 0.8,\n      "chunk_id": "tests\\\\integration\\\\test_installation_flow.py:239-344:class:TestInstallationValidation"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.0,\n    "reason": "No specific keywords matched - using default (bge_m3)",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 10 results. For unambiguous follow-up queries, use the chunk_id parameter (e.g., chunk_id=\'tests\\\\integration\\\\test_stemming_integration.py:136-166:decorated_definition:test_end_to_end_indexing_with_stemming\') instead of searching by name. Use find_similar_code to discover related implementations."\n}'}], 'isError': False})), metadata=None)
16:03:50 - Handling POST message
16:03:50 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:50 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"embedding model","k":3,"include_context":false},"_meta":{"claudecode/toolUseId":"toolu_015uxvsUoJvG1r9SpXyYZ68T"}},"jsonrpc":"2.0","id":60}'
16:03:50 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'embedding model', 'k': 3, 'include_context': False}, '_meta': {'claudecode/toolUseId': 'toolu_015uxvsUoJvG1r9SpXyYZ68T'}}, jsonrpc='2.0', id=60)
16:03:50 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'embedding model', 'k': 3, 'include_context': False}, '_meta': {'claudecode/toolUseId': 'toolu_015uxvsUoJvG1r9SpXyYZ68T'}}, jsonrpc='2.0', id=60)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243DDFC65D0>))
INFO:     ::1:52485 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:50 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F1DB3AD0>
16:03:50 - Processing request of type CallToolRequest
16:03:50 - Dispatching request of type CallToolRequest
16:03:50 - [TOOL_CALL] search_code
16:03:50 - [SEARCH] query='embedding model', k=3, mode='auto'
16:03:50 - [ROUTING] Query: 'embedding model...' → bge_m3 (confidence: 0.06, reason: Matched Workflow and configuration queries with confidence 0.06)
16:03:50 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:50 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:50 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:50 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:50 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:50 - [INIT] BM25Index created successfully
16:03:50 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:51 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:51 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:51 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:51 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:51 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:51 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:51 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:51 - [INIT] Loaded existing dense index with 1445 vectors
16:03:51 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:51 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:51 - Attempting to populate HybridSearcher with existing dense index data
16:03:51 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:51 - Searcher initialized for project: claude-context-local
16:03:51 - [MULTI_HOP] Starting 2-hop search for 'embedding model' (k=3, expansion=0.3, mode=semantic)
16:03:51 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:51 - Search mode: semantic, hybrid enabled: True
16:03:51 - Index manager search called with k=6, filters=None
16:03:51 - Index has 1445 total vectors
16:03:51 - [MULTI_HOP] Hop 1: Found 6 initial results (33.1ms)
16:03:51 - Index manager search called with k=2, filters=None
16:03:51 - Index has 1445 total vectors
16:03:51 - Index manager search called with k=2, filters=None
16:03:51 - Index has 1445 total vectors
16:03:51 - Index manager search called with k=2, filters=None
16:03:51 - Index has 1445 total vectors
16:03:51 - [MULTI_HOP] Hop 2: Discovered 2 new chunks (total: 8, 8.0ms)
16:03:51 - [MULTI_HOP] Re-ranking 8 total chunks by query relevance
16:03:51 - [MULTI_HOP] Complete: 3 results | Total=67ms (Hop1=33ms, Expansion=8ms, Rerank=25ms)
16:03:51 - Response sent
16:03:51 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=60, result={'content': [{'type': 'text', 'text': '{\n  "query": "embedding model",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_model_selection.py",\n      "lines": "131-185",\n      "kind": "class",\n      "score": 0.84,\n      "chunk_id": "tests\\\\unit\\\\test_model_selection.py:131-185:class:TestCodeEmbedderModelSupport"\n    },\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "794-865",\n      "kind": "method",\n      "score": 0.76,\n      "chunk_id": "search\\\\indexer.py:794-865:method:save_index",\n      "graph": {\n        "calls": [\n          "json"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "embeddings\\\\__init__.py",\n      "lines": "1-2",\n      "kind": "module",\n      "score": 0.69,\n      "chunk_id": "embeddings\\\\__init__.py:1-2:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 0.05555555555555555,\n    "reason": "Matched Workflow and configuration queries with confidence 0.06",\n    "scores": {\n      "coderankembed": 0.0,\n      "qwen3": 0.0,\n      "bge_m3": 0.05555555555555555\n    }\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:51 - Handling POST message
16:03:51 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:51 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"search index query","k":3,"model_key":"qwen3"},"_meta":{"claudecode/toolUseId":"toolu_01HkDUtkMf45vXCchReCF7Xb"}},"jsonrpc":"2.0","id":61}'
16:03:51 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'qwen3'}, '_meta': {'claudecode/toolUseId': 'toolu_01HkDUtkMf45vXCchReCF7Xb'}}, jsonrpc='2.0', id=61)
16:03:51 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'qwen3'}, '_meta': {'claudecode/toolUseId': 'toolu_01HkDUtkMf45vXCchReCF7Xb'}}, jsonrpc='2.0', id=61)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F0B47710>))
INFO:     ::1:52485 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:51 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0B45D90>
16:03:51 - Processing request of type CallToolRequest
16:03:51 - Dispatching request of type CallToolRequest
16:03:51 - [TOOL_CALL] search_code
16:03:51 - [SEARCH] query='search index query', k=3, mode='auto'
16:03:51 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:51 - [ROUTING] Using routed model: Qwen/Qwen3-Embedding-0.6B (key: qwen3)
16:03:51 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
16:03:51 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:51 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:51 - [INIT] BM25Index created successfully
16:03:51 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
16:03:52 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:52 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:52 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
16:03:52 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
16:03:52 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
16:03:52 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
16:03:52 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
16:03:52 - [INIT] Loaded existing dense index with 1445 vectors
16:03:52 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:52 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:52 - Attempting to populate HybridSearcher with existing dense index data
16:03:52 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:52 - Searcher initialized for project: claude-context-local
16:03:52 - [MULTI_HOP] Starting 2-hop search for 'search index query' (k=3, expansion=0.3, mode=semantic)
16:03:52 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:52 - Search mode: semantic, hybrid enabled: True
16:03:52 - Index manager search called with k=6, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - [MULTI_HOP] Hop 1: Found 6 initial results (114.8ms)
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - [MULTI_HOP] Hop 2: Discovered 3 new chunks (total: 9, 1.7ms)
16:03:52 - [MULTI_HOP] Re-ranking 9 total chunks by query relevance
16:03:52 - [MULTI_HOP] Complete: 3 results | Total=215ms (Hop1=115ms, Expansion=2ms, Rerank=97ms)
16:03:52 - Response sent
16:03:52 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=61, result={'content': [{'type': 'text', 'text': '{\n  "query": "search index query",\n  "results": [\n    {\n      "file": "search\\\\bm25_index.py",\n      "lines": "315-360",\n      "kind": "method",\n      "score": 0.86,\n      "chunk_id": "search\\\\bm25_index.py:315-360:method:search",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "float"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_hybrid_search.py",\n      "lines": "164-177",\n      "kind": "decorated_definition",\n      "score": 0.8,\n      "chunk_id": "tests\\\\unit\\\\test_hybrid_search.py:164-177:decorated_definition:test_search_not_ready"\n    },\n    {\n      "file": "scripts\\\\__init__.py",\n      "lines": "1-2",\n      "kind": "module",\n      "score": 0.73,\n      "chunk_id": "scripts\\\\__init__.py:1-2:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "qwen3",\n    "confidence": 1.0,\n    "reason": "User-specified override"\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:52 - Handling POST message
16:03:52 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:52 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"search index query","k":3,"model_key":"bge_m3"},"_meta":{"claudecode/toolUseId":"toolu_01LafBti8PiKLKy94FMLVjpg"}},"jsonrpc":"2.0","id":62}'
16:03:52 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'bge_m3'}, '_meta': {'claudecode/toolUseId': 'toolu_01LafBti8PiKLKy94FMLVjpg'}}, jsonrpc='2.0', id=62)
16:03:52 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'bge_m3'}, '_meta': {'claudecode/toolUseId': 'toolu_01LafBti8PiKLKy94FMLVjpg'}}, jsonrpc='2.0', id=62)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000244523C97D0>))
INFO:     ::1:52485 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:52 - Received message: <mcp.shared.session.RequestResponder object at 0x00000244523C9AD0>
16:03:52 - Processing request of type CallToolRequest
16:03:52 - Dispatching request of type CallToolRequest
16:03:52 - [TOOL_CALL] search_code
16:03:52 - [SEARCH] query='search index query', k=3, mode='auto'
16:03:52 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:52 - [ROUTING] Using routed model: BAAI/bge-m3 (key: bge_m3)
16:03:52 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
16:03:52 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:52 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
16:03:52 - [INIT] BM25Index created successfully
16:03:52 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
16:03:52 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:52 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:52 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
16:03:52 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
16:03:52 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
16:03:52 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
16:03:52 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
16:03:52 - [INIT] Loaded existing dense index with 1445 vectors
16:03:52 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:52 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:52 - Attempting to populate HybridSearcher with existing dense index data
16:03:52 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:52 - Searcher initialized for project: claude-context-local
16:03:52 - [MULTI_HOP] Starting 2-hop search for 'search index query' (k=3, expansion=0.3, mode=semantic)
16:03:52 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:52 - Search mode: semantic, hybrid enabled: True
16:03:52 - Index manager search called with k=6, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - [MULTI_HOP] Hop 1: Found 6 initial results (33.4ms)
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - Index manager search called with k=2, filters=None
16:03:52 - Index has 1445 total vectors
16:03:52 - [MULTI_HOP] Hop 2: Discovered 3 new chunks (total: 9, 15.8ms)
16:03:52 - [MULTI_HOP] Re-ranking 9 total chunks by query relevance
16:03:52 - [MULTI_HOP] Complete: 3 results | Total=82ms (Hop1=33ms, Expansion=16ms, Rerank=33ms)
16:03:52 - Response sent
16:03:52 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=62, result={'content': [{'type': 'text', 'text': '{\n  "query": "search index query",\n  "results": [\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "542-561",\n      "kind": "method",\n      "score": 0.8,\n      "chunk_id": "search\\\\indexer.py:542-561:method:get_similar_chunks",\n      "graph": {\n        "calls": [\n          "str",\n          "int",\n          "float"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\unit\\\\test_hybrid_search.py",\n      "lines": "239-271",\n      "kind": "decorated_definition",\n      "score": 0.78,\n      "chunk_id": "tests\\\\unit\\\\test_hybrid_search.py:239-271:decorated_definition:test_search_with_filters"\n    },\n    {\n      "file": "scripts\\\\__init__.py",\n      "lines": "1-2",\n      "kind": "module",\n      "score": 0.76,\n      "chunk_id": "scripts\\\\__init__.py:1-2:module"\n    }\n  ],\n  "routing": {\n    "model_selected": "bge_m3",\n    "confidence": 1.0,\n    "reason": "User-specified override"\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:53 - Handling POST message
16:03:53 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:53 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"search index query","k":3,"model_key":"coderankembed"},"_meta":{"claudecode/toolUseId":"toolu_01FmduyjCE3UGi3JaCo7wTLd"}},"jsonrpc":"2.0","id":63}'
16:03:53 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'coderankembed'}, '_meta': {'claudecode/toolUseId': 'toolu_01FmduyjCE3UGi3JaCo7wTLd'}}, jsonrpc='2.0', id=63)
16:03:53 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'search index query', 'k': 3, 'model_key': 'coderankembed'}, '_meta': {'claudecode/toolUseId': 'toolu_01FmduyjCE3UGi3JaCo7wTLd'}}, jsonrpc='2.0', id=63)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x000002445227AB90>))
INFO:     ::1:52485 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:53 - Received message: <mcp.shared.session.RequestResponder object at 0x00000242BF114610>
16:03:53 - Processing request of type CallToolRequest
16:03:53 - Dispatching request of type CallToolRequest
16:03:53 - [TOOL_CALL] search_code
16:03:53 - [SEARCH] query='search index query', k=3, mode='auto'
16:03:53 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:53 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:03:53 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:03:53 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:03:53 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:03:53 - [INIT] BM25Index created successfully
16:03:53 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:03:53 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:53 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:53 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:03:53 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:03:53 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:03:53 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:03:53 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:03:53 - [INIT] Loaded existing dense index with 1445 vectors
16:03:53 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:53 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:53 - Attempting to populate HybridSearcher with existing dense index data
16:03:53 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:53 - Searcher initialized for project: claude-context-local
16:03:53 - [MULTI_HOP] Starting 2-hop search for 'search index query' (k=3, expansion=0.3, mode=semantic)
16:03:53 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:53 - Search mode: semantic, hybrid enabled: True
16:03:53 - Index manager search called with k=6, filters=None
16:03:53 - Index has 1445 total vectors
16:03:53 - [MULTI_HOP] Hop 1: Found 6 initial results (29.3ms)
16:03:53 - Index manager search called with k=2, filters=None
16:03:53 - Index has 1445 total vectors
16:03:53 - Index manager search called with k=2, filters=None
16:03:53 - Index has 1445 total vectors
16:03:53 - Index manager search called with k=2, filters=None
16:03:53 - Index has 1445 total vectors
16:03:53 - [MULTI_HOP] Hop 2: Discovered 3 new chunks (total: 9, 11.7ms)
16:03:53 - [MULTI_HOP] Re-ranking 9 total chunks by query relevance
16:03:53 - [MULTI_HOP] Complete: 3 results | Total=66ms (Hop1=29ms, Expansion=12ms, Rerank=25ms)
16:03:53 - Response sent
16:03:53 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=63, result={'content': [{'type': 'text', 'text': '{\n  "query": "search index query",\n  "results": [\n    {\n      "file": "tests\\\\unit\\\\test_token_efficiency.py",\n      "lines": "254-256",\n      "kind": "method",\n      "score": 0.9,\n      "chunk_id": "tests\\\\unit\\\\test_token_efficiency.py:254-256:method:__init__"\n    },\n    {\n      "file": "search\\\\indexer.py",\n      "lines": "422-477",\n      "kind": "method",\n      "score": 0.57,\n      "chunk_id": "search\\\\indexer.py:422-477:method:search",\n      "graph": {\n        "calls": [\n          "np.ndarray",\n          "int",\n          "str",\n          "float",\n          "logging"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\integration\\\\test_full_flow.py",\n      "lines": "115-172",\n      "kind": "method",\n      "score": 0.53,\n      "chunk_id": "tests\\\\integration\\\\test_full_flow.py:115-172:method:test_real_project_indexing_and_search"\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 1.0,\n    "reason": "User-specified override"\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
16:03:53 - Handling POST message
16:03:53 - Parsed session ID: 76905a4e-cd02-4784-8099-a9622b85a43a
16:03:53 - Received JSON: b'{"method":"tools/call","params":{"name":"search_code","arguments":{"query":"hybrid search BM25 dense","k":3,"search_mode":"semantic"},"_meta":{"claudecode/toolUseId":"toolu_01ECsAMDPShBEsEgViiP19qE"}},"jsonrpc":"2.0","id":64}'
16:03:53 - Validated client message: root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'hybrid search BM25 dense', 'k': 3, 'search_mode': 'semantic'}, '_meta': {'claudecode/toolUseId': 'toolu_01ECsAMDPShBEsEgViiP19qE'}}, jsonrpc='2.0', id=64)
16:03:53 - Sending session message to writer: SessionMessage(message=JSONRPCMessage(root=JSONRPCRequest(method='tools/call', params={'name': 'search_code', 'arguments': {'query': 'hybrid search BM25 dense', 'k': 3, 'search_mode': 'semantic'}, '_meta': {'claudecode/toolUseId': 'toolu_01ECsAMDPShBEsEgViiP19qE'}}, jsonrpc='2.0', id=64)), metadata=ServerMessageMetadata(related_request_id=None, request_context=<starlette.requests.Request object at 0x00000243F0EB6490>))
INFO:     ::1:52485 - "POST /messages/?session_id=76905a4ecd0247848099a9622b85a43a HTTP/1.1" 202 Accepted
16:03:53 - Received message: <mcp.shared.session.RequestResponder object at 0x00000243F0F40A50>
16:03:53 - Processing request of type CallToolRequest
16:03:53 - Dispatching request of type CallToolRequest
16:03:53 - [TOOL_CALL] search_code
16:03:53 - [SEARCH] query='hybrid search BM25 dense', k=3, mode='semantic'
16:03:53 - [ROUTING] Query: 'hybrid search BM25 dense...' → coderankembed (confidence: 0.07, reason: Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07)
16:03:53 - [GET_SEARCHER] Initializing searcher for project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
16:03:53 - [ROUTING] Using routed model: nomic-ai/CodeRankEmbed (key: coderankembed)
16:03:53 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
16:03:53 - [GET_SEARCHER] Using storage directory: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:03:53 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
16:03:53 - [INIT] BM25Index created successfully
16:03:53 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
16:03:53 - BM25 index loaded from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 with 1445 documents (version=2, stemming=True)
16:03:53 - [INIT] Loaded existing BM25 index with 1445 documents
16:03:53 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
16:03:53 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
16:03:53 - Loaded call graph: 2721 nodes, 5874 edges ← C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
16:03:53 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
16:03:53 - Loading existing index from C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
16:03:53 - [INIT] Loaded existing dense index with 1445 vectors
16:03:53 - [INIT] HybridSearcher initialized - BM25: 1445 docs, Dense: 1445 vectors
16:03:53 - [INIT] Ready status: BM25=True, Dense=True, Overall=True
16:03:54 - Attempting to populate HybridSearcher with existing dense index data
16:03:54 - HybridSearcher initialized (BM25: 0.4, Dense: 0.6)
16:03:54 - Searcher initialized for project: claude-context-local
16:03:54 - [MULTI_HOP] Starting 2-hop search for 'hybrid search BM25 dense' (k=3, expansion=0.3, mode=semantic)
16:03:54 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
16:03:54 - Search mode: semantic, hybrid enabled: True
16:03:54 - Index manager search called with k=6, filters=None
16:03:54 - Index has 1445 total vectors
16:03:54 - [MULTI_HOP] Hop 1: Found 6 initial results (26.6ms)
16:03:54 - Index manager search called with k=2, filters=None
16:03:54 - Index has 1445 total vectors
16:03:54 - Index manager search called with k=2, filters=None
16:03:54 - Index has 1445 total vectors
16:03:54 - Index manager search called with k=2, filters=None
16:03:54 - Index has 1445 total vectors
16:03:54 - [MULTI_HOP] Hop 2: Discovered 0 new chunks (total: 6, 7.7ms)
16:03:54 - [MULTI_HOP] Re-ranking 6 total chunks by query relevance
16:03:54 - [MULTI_HOP] Complete: 3 results | Total=63ms (Hop1=27ms, Expansion=8ms, Rerank=28ms)
16:03:54 - Response sent
16:03:54 - Sending message via SSE: SessionMessage(message=JSONRPCMessage(root=JSONRPCResponse(jsonrpc='2.0', id=64, result={'content': [{'type': 'text', 'text': '{\n  "query": "hybrid search BM25 dense",\n  "results": [\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "57-1400",\n      "kind": "class",\n      "score": 0.62,\n      "chunk_id": "search\\\\hybrid_searcher.py:57-1400:class:HybridSearcher",\n      "graph": {\n        "calls": [\n          "str",\n          "float",\n          "int",\n          "bool",\n          "SearchResult",\n          "set",\n          "numpy",\n          "embeddings.embedder.EmbeddingResult",\n          ".config.get_search_config",\n          ".searcher.SearchResult",\n          ".config.SearchConfigManager",\n          "pathlib.Path",\n          "embeddings.embedder.CodeEmbedder",\n          "traceback",\n          ".reranker.SearchResult"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "search\\\\hybrid_searcher.py",\n      "lines": "60-179",\n      "kind": "method",\n      "score": 0.56,\n      "chunk_id": "search\\\\hybrid_searcher.py:60-179:method:__init__",\n      "graph": {\n        "calls": [\n          "str",\n          "float",\n          "int",\n          "bool"\n        ],\n        "called_by": []\n      }\n    },\n    {\n      "file": "tests\\\\integration\\\\test_hybrid_search_integration.py",\n      "lines": "289-321",\n      "kind": "decorated_definition",\n      "score": 0.55,\n      "chunk_id": "tests\\\\integration\\\\test_hybrid_search_integration.py:289-321:decorated_definition:test_bm25_vs_dense_results_differ"\n    }\n  ],\n  "routing": {\n    "model_selected": "coderankembed",\n    "confidence": 0.07142857142857142,\n    "reason": "Matched Specialized algorithms (Merkle trees, RRF reranking) with confidence 0.07",\n    "scores": {\n      "coderankembed": 0.07142857142857142,\n      "qwen3": 0.03773584905660377,\n      "bge_m3": 0.0\n    }\n  },\n  "system_message": "Found 3 results. Use chunk_id from results for precise follow-up. Results include call graph data. Use get_callers/get_callees for detailed relationship analysis."\n}'}], 'isError': False})), metadata=None)
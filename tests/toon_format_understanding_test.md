# TOON Format Understanding Test Plan

**Purpose**: Verify that Claude Code agent can correctly interpret TOON tabular format in MCP tool responses.

**Instructions**: Execute this test plan in a fresh Claude Code instance (new conversation). Write all answers to the file specified in Step 5.

---

## Prerequisites

1. MCP server must be running with TOON format enabled
2. Project must be indexed: `claude-context-local` (this codebase)
3. Output format set to TOON

---

## Step 1: Configure TOON Format

Run the following command to set output format to TOON:

```
Start the interactive menu and navigate to:
3. Search Configuration → A. Configure Output Format → 3. TOON
```

Or via MCP tool (if available):

```python
# Set TOON format via config
from search.config import SearchConfigManager
mgr = SearchConfigManager()
cfg = mgr.load_config()
cfg.output.format = 'toon'
mgr.save_config(cfg)
```

**Verification**: Check that format is set:

```python
from search.config import get_search_config
print(get_search_config().output.format)  # Should print: toon
```

---

## Step 2: Execute Test Query

Run this MCP search to get TOON-formatted results:

```
/find_connections --chunk_id "mcp_server/output_formatter.py:109-172:function:_to_toon_format"
```

This should return results about the `_to_toon_format` function with:

- Direct callers (if any)
- Indirect callers (if any)
- Similar code chunks

**Expected**: Response will contain TOON-formatted arrays with headers like:

- `"direct_callers[N]{chunk_id,kind,score}"`
- `"similar_code[N]{chunk_id,kind,score}"`

---

## Step 3: Interpret TOON Format

Look at the response and answer the following questions. **Write your answers in the test results file (see Step 5)**.

### Question 1: Format Note

**Q1**: What is the value of the `_format_note` field in the response?

**Your answer**: [Write the exact string here]

---

### Question 2: Header Parsing

Identify a TOON header from the response (e.g., `"direct_callers[5]{chunk_id,kind,score}"`).

**Q2a**: What is the array name?

**Your answer**: [e.g., "direct_callers"]

**Q2b**: How many elements are in this array (count)?

**Your answer**: [e.g., 5]

**Q2c**: What are the field names in order?

**Your answer**: [e.g., "chunk_id, kind, score"]

---

### Question 3: Row Value Extraction

Using the same TOON array from Q2, look at the first row of values.

Example format:

```json
"direct_callers[5]{chunk_id,kind,score}": [
  ["mcp_server/server.py:124-149:function:handle_call_tool", "function", 0.95],
  ...
]
```

**Q3a**: What is the chunk_id of the first caller (first value in first row)?

**Your answer**: [Write the full chunk_id string]

**Q3b**: What is the kind of the first caller (second value in first row)?

**Your answer**: [e.g., "function", "method", "class"]

**Q3c**: What is the score of the first caller (third value in first row)?

**Your answer**: [e.g., 0.95]

---

### Question 4: Data Reconstruction

Based on the TOON format, reconstruct the first result as a standard JSON object.

**Q4**: Write the reconstructed object in JSON format:

**Your answer**:

```json
{
  "chunk_id": "...",
  "kind": "...",
  "score": ...
}
```

---

### Question 5: Multiple Arrays

If the response contains multiple TOON arrays (e.g., both `direct_callers` and `similar_code`):

**Q5a**: How many total TOON arrays are in the response?

**Your answer**: [e.g., 2, 3, or "none"]

**Q5b**: List all TOON array names (from headers):

**Your answer**: [e.g., "direct_callers, similar_code, indirect_callers"]

---

### Question 6: Understanding Check

**Q6**: In your own words, explain how TOON format works. What are the benefits and how do you parse it?

**Your answer**: [Write 2-3 sentences explaining your understanding]

---

## Step 4: Execute Second Test Query (Optional)

For additional verification, run a search query:

```
/search_code --query "format response output toon" --k 3 --output_format "toon"
```

**Q7**: Did this query also return TOON format? Describe what you see.

**Your answer**: [Describe the response format]

---

## Step 5: Write Test Results

**CRITICAL**: Write all your answers (Q1-Q7) to this file:

```
F:/RD_PROJECTS/COMPONENTS/claude-context-local/tests/toon_format_test_results.txt
```

Use this template:

```
=== TOON Format Understanding Test Results ===
Timestamp: [Current date/time]
Tester: Claude Code Agent (fresh instance)

=== Question 1: Format Note ===
[Your answer]

=== Question 2: Header Parsing ===
Q2a - Array name: [Your answer]
Q2b - Element count: [Your answer]
Q2c - Field names: [Your answer]

=== Question 3: Row Value Extraction ===
Q3a - First chunk_id: [Your answer]
Q3b - First kind: [Your answer]
Q3c - First score: [Your answer]

=== Question 4: Data Reconstruction ===
[Your JSON object]

=== Question 5: Multiple Arrays ===
Q5a - Total arrays: [Your answer]
Q5b - Array names: [Your answer]

=== Question 6: Understanding Check ===
[Your explanation]

=== Question 7: Second Query (Optional) ===
[Your answer]

=== Overall Assessment ===
Did you successfully interpret the TOON format? (Yes/No): [Your answer]
Confidence level (1-10): [Your answer]
Any confusion or difficulties?: [Your answer]
```

---

## Step 6: Report Completion

After writing all answers to `toon_format_test_results.txt`, respond with:

**"TOON format test completed. Results written to tests/toon_format_test_results.txt"**

---

## Success Criteria (for verification)

When you resume the original conversation, the verifier will check:

1. ✅ All questions answered correctly
2. ✅ TOON header parsed correctly (array name, count, fields)
3. ✅ Row values extracted correctly (maintaining field order)
4. ✅ Data successfully reconstructed from tabular format
5. ✅ Agent understands TOON format benefits (token reduction, tabular structure)
6. ✅ No confusion about the format

**Expected outcome**: Agent should demonstrate clear understanding of TOON format with 90%+ accuracy on value extraction and parsing.

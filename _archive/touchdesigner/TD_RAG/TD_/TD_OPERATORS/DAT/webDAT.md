# DAT webDAT

## Overview

The Web DAT fetches pages of data from a web connection.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `url` | URL |  | The url address of the web page to be retrieved. |
| `fetch` | Fetch |  | The data will be fetched when this button is pressed. Use this method to retrieve simple single pages from the internet. By default the Web DAT will stall the process until the whole page has been ... |
| `method` | Submit Method |  | Currently only POST is implemented, though this will be expanded with other techniques such as GET. |
| `submitfetch` | Submit and Fetch |  | Post all the name/value pairs from the input DAT to the server, then fetch the page specified in the URL parameter.      Use this method to post data to a web server before retrieving the page. The... |
| `includeheader` | Include Header in Output |  | Includes the HTTP header in the output. |
| `timeout` | Timeout |  | If this value is 0 the fetch request will never timeout. Any other value is how many milliseconds before the fetch times out. |
| `disconnect` | Disconnect |  | Closes the session. |
| `asyncfetch` | Asynchronous Fetch |  | Turn on this option to allow the download to occur in the background. You can use a DAT Execute DAT to do something when the data finally arrives. |
| `verifypeer` | Verify Peer Certificate |  | Enables TLS (transport layer security) certificate verification. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT webDAT operator
webdat_op = op('webdat1')

# Get/set parameters
freq_value = webdat_op.par.active.eval()
webdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
webdat_op = op('webdat1')
output_op = op('output1')

webdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(webdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*

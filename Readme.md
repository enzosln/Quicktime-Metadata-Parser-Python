## Quicktime Parser

Parse metadata from quicktime `.mov` files.

### Installation

You can install this tool as a package:

```
git clone https://github.com/enzosln/Quicktime-Metadata-Parser-Python
```

And import the script `parser.py` where you want to use him.
The class Mov have to receive the path of your mov file.
Documentation is not already available :(



### How to use

Here's a brief code example that showcases how to use the script:

```python
import parser.py as QtParser

qt = QtParser.Mov("path/to/file.mov")
qt.parse()

#retrieve the creation-time as a string (the actual creation time, not the file-system creation time)
date = qt.metadata["creation time"]

#traverse all key-value pairs of the metadata
for key in qt.metadata.keys():
  print(key+": "+str(qt.metadata[key]))
```

Note that all metadata key's are converted to lower-case and stripped of leading and trailing spaces.

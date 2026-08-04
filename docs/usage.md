# Installation and use

## Install

Install the platform-specific wheel together with WeasyPrint:

```bash
python -m pip install procitec_weasyprint_libs-*.whl weasyprint
```

The package installs `procitec_weasyprint_libs.pth`. Python processes this file during site initialization and calls:

```python
import weasyprintlibs_native

weasyprintlibs_native.activate()
```

No explicit activation is required in application code:

```python
from weasyprint import HTML

HTML(string="<h1>Hello</h1>").write_pdf("output.pdf")
```

## Linux runtime

The native libraries are installed below:

```text
site-packages/weasyprintlibs_native/lib/
```

Fontconfig configuration and runtime data are installed below:

```text
site-packages/weasyprintlibs_native/etc/fonts/
site-packages/weasyprintlibs_native/share/
```

The loader configures Fontconfig before loading Pango and related libraries. The wheel does not necessarily include font files; the operating system must provide usable fonts unless fonts are added explicitly to the package.

## Windows runtime

The DLL directory is installed below:

```text
site-packages/weasyprintlibs_native/bin/
```

The loader adds this directory with `os.add_dll_directory()` and keeps the returned handle alive for the process lifetime.

## Troubleshooting

To inspect native libraries loaded by a Linux process:

```bash
LD_DEBUG=libs,files \
LD_DEBUG_OUTPUT=/tmp/weasyprint-loader \
python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"
```

The files actually mapped into the process are also visible in `/proc/<pid>/maps`.

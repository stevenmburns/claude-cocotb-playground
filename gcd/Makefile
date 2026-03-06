TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/gcd.v
TOPLEVEL = gcd
MODULE = test_gcd
SIM = verilator
EXTRA_ARGS = --timing

# Paths to venv and locally-installed verilator (no system install required)
VENV := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../.venv)
VERILATOR_BIN := /home/smburns/.local/bin
export PATH := $(VENV)/bin:$(VERILATOR_BIN):$(PATH)
PYTHON_BIN := $(VENV)/bin/python

include $(shell $(VENV)/bin/cocotb-config --makefiles)/Makefile.sim

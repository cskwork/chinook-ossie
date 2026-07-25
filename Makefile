# Chinook semantic models — validation entry points.
#
# `make validate` checks SPEC COMPLIANCE (does the YAML satisfy the Ossie schema?).
# `make verify`   checks REALITY      (do the tables/columns actually exist?).
# Only the first one is generic; see docs/verification.md for the second.

MODELS := $(shell find models -name '*.yaml' 2>/dev/null | sort)
SCHEMA := schema/osi-schema.json
VALIDATE := uv run scripts/validate.py

# Source of truth: the Chinook reference schema, fetched on demand into .evidence/
# (git-ignored — evidence is reproducible, not committed).
DDL     := .evidence/chinook_pg.sql
DDL_URL := https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_PostgreSql.sql

.PHONY: help validate verify check evidence

help:
	@echo "make validate                 - validate every model under models/"
	@echo "make validate FILE=<m.yaml>   - validate a single model"
	@echo "make evidence                 - fetch the Chinook DDL into .evidence/"
	@echo "make verify                   - compare models against that DDL"
	@echo "make check                    - validate + verify"

validate:
ifdef FILE
	@$(VALIDATE) $(FILE) --schema $(SCHEMA)
else
	@test -n "$(MODELS)" || { echo "no models found under models/"; exit 1; }
	@fail=0; for m in $(MODELS); do \
	  echo "######## $$m"; \
	  $(VALIDATE) $$m --schema $(SCHEMA) || fail=1; \
	done; \
	if [ $$fail -ne 0 ]; then echo; echo "validation FAILED"; exit 1; fi; \
	echo; echo "all models PASSED"
endif

evidence: $(DDL)

$(DDL):
	@mkdir -p $(dir $(DDL))
	@curl -fsSL "$(DDL_URL)" -o $(DDL)
	@echo "fetched $(DDL) ($$(wc -l < $(DDL) | tr -d ' ') lines)"

# Does the model tell the truth? Tables, columns, datatypes and primary keys are
# compared against the real Chinook DDL. Fails the build on any divergence.
verify: $(DDL)
	@uv run scripts/verify_ddl.py $(MODELS) --ddl $(DDL)

check: validate verify

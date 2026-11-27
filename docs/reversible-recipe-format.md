# Reversible GSI recipe format

Recipes should be JSON and contain: id, scope, preconditions, target path, operation, expected source hash, resulting hash, backup location, rollback operation, and evidence/reference. No recipe should be applied automatically. Recipes must reject absolute paths outside the staged tree and symlink traversal. Recipe review and dry-run precede any write.

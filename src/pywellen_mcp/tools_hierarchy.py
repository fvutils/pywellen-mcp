"""Hierarchy navigation tools for exploring waveform structure."""

from typing import Any, Dict, List, Optional, Pattern
import re

from .session import SessionManager
from .errors import SessionError, QueryError, ErrorCode


class HierarchyTools:
    """Tools for navigating waveform hierarchy."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def hierarchy_list_top_scopes(self, session_id: str) -> Dict[str, Any]:
        """
        List all top-level scopes in the waveform hierarchy.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with list of top-level scopes
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        hierarchy = session.hierarchy
        scopes = []

        for scope in hierarchy.top_scopes():
            scope_info = {
                "name": scope.name(hierarchy),
                "full_name": scope.full_name(hierarchy),
                "type": scope.scope_type(),
            }

            # Count children
            num_vars = sum(1 for _ in scope.vars(hierarchy))
            num_scopes = sum(1 for _ in scope.scopes(hierarchy))

            scope_info["num_variables"] = num_vars
            scope_info["num_child_scopes"] = num_scopes

            scopes.append(scope_info)

        return {
            "session_id": session_id,
            "top_scopes": scopes,
            "count": len(scopes),
        }

    async def hierarchy_get_scope(
        self,
        session_id: str,
        scope_path: str,
        include_variables: bool = True,
        include_child_scopes: bool = True,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific scope.

        Args:
            session_id: Session identifier
            scope_path: Dot-separated scope path (e.g., "top.cpu.alu")
            include_variables: Include list of variables in scope
            include_child_scopes: Include list of child scopes

        Returns:
            Dictionary with scope details
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        hierarchy = session.hierarchy

        # Find the scope by traversing the path
        scope = self._find_scope_by_path(hierarchy, scope_path)
        if scope is None:
            raise QueryError(
                f"Scope not found: {scope_path}",
                code=ErrorCode.SCOPE_NOT_FOUND,
                context={"session_id": session_id, "scope_path": scope_path},
            )

        result = {
            "session_id": session_id,
            "scope_path": scope_path,
            "name": scope.name(hierarchy),
            "full_name": scope.full_name(hierarchy),
            "type": scope.scope_type(),
        }

        # Add variables if requested
        if include_variables:
            variables = []
            for var in scope.vars(hierarchy):
                var_info = {
                    "name": var.name(hierarchy),
                    "full_name": var.full_name(hierarchy),
                    "type": var.var_type(),
                    "bitwidth": var.bitwidth(),
                    "direction": var.direction(),
                }
                variables.append(var_info)
            result["variables"] = variables
            result["num_variables"] = len(variables)

        # Add child scopes if requested
        if include_child_scopes:
            child_scopes = []
            for child in scope.scopes(hierarchy):
                child_info = {
                    "name": child.name(hierarchy),
                    "full_name": child.full_name(hierarchy),
                    "type": child.scope_type(),
                }
                child_scopes.append(child_info)
            result["child_scopes"] = child_scopes
            result["num_child_scopes"] = len(child_scopes)

        return result

    async def hierarchy_list_variables(
        self,
        session_id: str,
        scope_path: Optional[str] = None,
        var_types: Optional[List[str]] = None,
        direction: Optional[str] = None,
        min_bitwidth: Optional[int] = None,
        max_bitwidth: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List variables with optional filtering.

        Args:
            session_id: Session identifier
            scope_path: Optional scope path to limit search (None = all variables)
            var_types: Filter by variable types (e.g., ["Wire", "Reg"])
            direction: Filter by direction ("Input", "Output", "InOut", etc.)
            min_bitwidth: Minimum bitwidth (inclusive)
            max_bitwidth: Maximum bitwidth (inclusive)
            limit: Maximum number of results (default: 100)
            offset: Skip first N results (for pagination)

        Returns:
            Dictionary with filtered variable list
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        hierarchy = session.hierarchy

        # Get variable iterator
        if scope_path:
            scope = self._find_scope_by_path(hierarchy, scope_path)
            if scope is None:
                raise QueryError(
                    f"Scope not found: {scope_path}",
                    code=ErrorCode.SCOPE_NOT_FOUND,
                    context={"session_id": session_id, "scope_path": scope_path},
                )
            var_iter = scope.vars(hierarchy)
        else:
            var_iter = hierarchy.all_vars()

        # Apply filters and collect results
        variables = []
        skipped = 0
        total_matched = 0

        for var in var_iter:
            # Apply type filter
            if var_types and var.var_type() not in var_types:
                continue

            # Apply direction filter
            if direction and var.direction() != direction:
                continue

            # Apply bitwidth filters
            bitwidth = var.bitwidth()
            if bitwidth is not None:
                if min_bitwidth is not None and bitwidth < min_bitwidth:
                    continue
                if max_bitwidth is not None and bitwidth > max_bitwidth:
                    continue

            total_matched += 1

            # Apply pagination
            if skipped < offset:
                skipped += 1
                continue

            if len(variables) >= limit:
                continue

            # Add to results
            var_info = {
                "name": var.name(hierarchy),
                "full_name": var.full_name(hierarchy),
                "type": var.var_type(),
                "bitwidth": bitwidth,
                "direction": var.direction(),
                "is_real": var.is_real(),
                "is_string": var.is_string(),
                "is_1bit": var.is_1bit(),
            }

            # Add optional fields if available
            enum_type = var.enum_type(hierarchy)
            if enum_type:
                enum_name, enum_values = enum_type
                var_info["enum_type"] = {
                    "name": enum_name,
                    "values": [{"bits": bits, "name": name} for bits, name in enum_values],
                }

            vhdl_type = var.vhdl_type_name(hierarchy)
            if vhdl_type:
                var_info["vhdl_type"] = vhdl_type

            variables.append(var_info)

        return {
            "session_id": session_id,
            "scope_path": scope_path,
            "filters": {
                "var_types": var_types,
                "direction": direction,
                "min_bitwidth": min_bitwidth,
                "max_bitwidth": max_bitwidth,
            },
            "variables": variables,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(variables),
                "total_matched": total_matched,
                "has_more": total_matched > offset + len(variables),
            },
        }

    async def hierarchy_search(
        self,
        session_id: str,
        pattern: str,
        search_in: str = "both",
        case_sensitive: bool = False,
        regex: bool = False,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Search hierarchy by name pattern.

        Args:
            session_id: Session identifier
            pattern: Search pattern (regex or literal string)
            search_in: "scopes", "variables", or "both"
            case_sensitive: Case-sensitive matching
            regex: Treat pattern as regex (otherwise substring match)
            limit: Maximum results per category

        Returns:
            Dictionary with matching scopes and/or variables
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        if search_in not in ("scopes", "variables", "both"):
            raise QueryError(
                f"Invalid search_in value: {search_in}",
                code=ErrorCode.INVALID_PARAMETER,
                context={"search_in": search_in, "valid_values": ["scopes", "variables", "both"]},
            )

        hierarchy = session.hierarchy

        # Compile pattern
        try:
            if regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(pattern, flags)
            else:
                # Substring search - escape pattern and make it case-insensitive if needed
                escaped = re.escape(pattern)
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(escaped, flags)
        except re.error as e:
            raise QueryError(
                f"Invalid regex pattern: {e}",
                code=ErrorCode.INVALID_PARAMETER,
                context={"pattern": pattern, "error": str(e)},
            )

        result = {
            "session_id": session_id,
            "pattern": pattern,
            "search_in": search_in,
            "case_sensitive": case_sensitive,
            "regex": regex,
        }

        # Search scopes if requested
        if search_in in ("scopes", "both"):
            matching_scopes = []
            for scope in self._iter_all_scopes(hierarchy):
                full_name = scope.full_name(hierarchy)
                if compiled_pattern.search(full_name):
                    if len(matching_scopes) < limit:
                        matching_scopes.append(
                            {
                                "name": scope.name(hierarchy),
                                "full_name": full_name,
                                "type": scope.scope_type(),
                            }
                        )
            result["matching_scopes"] = matching_scopes
            result["num_scopes"] = len(matching_scopes)
            result["scopes_truncated"] = len(matching_scopes) >= limit

        # Search variables if requested
        if search_in in ("variables", "both"):
            matching_vars = []
            for var in hierarchy.all_vars():
                full_name = var.full_name(hierarchy)
                if compiled_pattern.search(full_name):
                    if len(matching_vars) < limit:
                        matching_vars.append(
                            {
                                "name": var.name(hierarchy),
                                "full_name": full_name,
                                "type": var.var_type(),
                                "bitwidth": var.bitwidth(),
                            }
                        )
            result["matching_variables"] = matching_vars
            result["num_variables"] = len(matching_vars)
            result["variables_truncated"] = len(matching_vars) >= limit

        return result

    def _find_scope_by_path(self, hierarchy, scope_path: str):
        """
        Find a scope by its dot-separated path.

        Args:
            hierarchy: Hierarchy object
            scope_path: Dot-separated path (e.g., "top.cpu.alu")

        Returns:
            Scope object or None if not found
        """
        parts = scope_path.split(".")

        # Start with top scopes
        current_scopes = list(hierarchy.top_scopes())

        for i, part in enumerate(parts):
            # Find matching scope at current level
            found = None
            for scope in current_scopes:
                if scope.name(hierarchy) == part:
                    found = scope
                    break

            if found is None:
                return None

            # If this is the last part, we found it
            if i == len(parts) - 1:
                return found

            # Otherwise, descend to child scopes
            current_scopes = list(found.scopes(hierarchy))

        return None

    def _iter_all_scopes(self, hierarchy):
        """
        Recursively iterate over all scopes in hierarchy.

        Args:
            hierarchy: Hierarchy object

        Yields:
            Scope objects
        """
        def recurse(scope):
            yield scope
            for child in scope.scopes(hierarchy):
                yield from recurse(child)

        for top in hierarchy.top_scopes():
            yield from recurse(top)

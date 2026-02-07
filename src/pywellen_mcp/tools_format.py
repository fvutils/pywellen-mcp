"""
Value formatting and interpretation tools.

This module provides tools for converting signal values between different
representations (binary, hex, decimal, signed/unsigned) to support various
debugging and analysis workflows.
"""

from typing import Literal, Dict, Any, Optional


async def format_value(
    value: str,
    from_format: Literal["auto", "binary", "hex", "decimal", "octal"] = "auto",
    to_format: Literal["binary", "hex", "decimal", "octal"] = "hex",
    bitwidth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convert signal value between different representations.
    
    Useful for:
    - Converting waveform values to preferred radix
    - Formatting values for display or export
    - Preparing values for comparison
    
    Args:
        value: Input value to convert
        from_format: Input format (auto detects from prefix)
        to_format: Desired output format
        bitwidth: Optional bit width for padding
        
    Returns:
        {
            "original": str,
            "formatted": str,
            "numeric": int | None,
            "format": str
        }
    """
    # Parse input value
    numeric_value = None
    
    try:
        if from_format == "auto":
            # Auto-detect format
            value_str = str(value).strip()
            if value_str.startswith("0x") or value_str.startswith("0X"):
                numeric_value = int(value_str, 16)
            elif value_str.startswith("0b") or value_str.startswith("0B"):
                numeric_value = int(value_str, 2)
            elif value_str.startswith("0o") or value_str.startswith("0O"):
                numeric_value = int(value_str, 8)
            else:
                # Try as decimal, fallback to special handling
                try:
                    numeric_value = int(value_str, 10)
                except ValueError:
                    # Handle X, Z, and other special VCD values
                    if all(c in "01xXzZ-" for c in value_str):
                        # Binary-like representation with special values
                        # Convert to numeric where possible
                        clean = value_str.replace("x", "0").replace("X", "0")
                        clean = clean.replace("z", "0").replace("Z", "0")
                        clean = clean.replace("-", "0")
                        if clean:
                            numeric_value = int(clean, 2)
        else:
            # Use specified format
            bases = {
                "binary": 2,
                "hex": 16,
                "decimal": 10,
                "octal": 8,
            }
            numeric_value = int(str(value), bases[from_format])
    except (ValueError, KeyError):
        # Non-numeric value, return as-is
        return {
            "original": str(value),
            "formatted": str(value),
            "numeric": None,
            "format": to_format,
        }
    
    # Format output
    formatted = None
    
    if numeric_value is None:
        # Non-numeric value that wasn't caught earlier
        return {
            "original": str(value),
            "formatted": str(value),
            "numeric": None,
            "format": to_format,
        }
    
    if to_format == "binary":
        formatted = bin(numeric_value)
        if bitwidth and formatted.startswith("0b"):
            # Pad to specified width
            bits = formatted[2:]
            if len(bits) < bitwidth:
                bits = "0" * (bitwidth - len(bits)) + bits
            formatted = "0b" + bits
    elif to_format == "hex":
        formatted = hex(numeric_value)
        if bitwidth and formatted.startswith("0x"):
            # Calculate required hex digits
            hex_digits = (bitwidth + 3) // 4
            hex_part = formatted[2:]
            if len(hex_part) < hex_digits:
                hex_part = "0" * (hex_digits - len(hex_part)) + hex_part
            formatted = "0x" + hex_part
    elif to_format == "decimal":
        formatted = str(numeric_value)
    elif to_format == "octal":
        formatted = oct(numeric_value)
    
    return {
        "original": str(value),
        "formatted": formatted,
        "numeric": numeric_value,
        "format": to_format,
    }


async def format_as_signed(
    value: str,
    bitwidth: int,
    input_format: Literal["auto", "binary", "hex", "decimal"] = "auto",
) -> Dict[str, Any]:
    """
    Interpret bit vector as signed integer using two's complement.
    
    Useful for:
    - Displaying signed register values
    - Converting unsigned waveform values to signed interpretation
    - Analyzing arithmetic operations
    
    Args:
        value: Input value (unsigned interpretation)
        bitwidth: Number of bits in the value
        input_format: Format of input value
        
    Returns:
        {
            "unsigned": int,
            "signed": int,
            "hex": str,
            "binary": str,
            "is_negative": bool
        }
    """
    # Parse input value
    try:
        if input_format == "auto":
            value_str = str(value).strip()
            if value_str.startswith("0x") or value_str.startswith("0X"):
                unsigned_value = int(value_str, 16)
            elif value_str.startswith("0b") or value_str.startswith("0B"):
                unsigned_value = int(value_str, 2)
            else:
                unsigned_value = int(value_str, 10)
        else:
            bases = {
                "binary": 2,
                "hex": 16,
                "decimal": 10,
            }
            unsigned_value = int(str(value), bases[input_format])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid value '{value}': {e}")
    
    # Check if value fits in bitwidth
    max_unsigned = (1 << bitwidth) - 1
    if unsigned_value > max_unsigned:
        raise ValueError(f"Value {unsigned_value} exceeds bitwidth {bitwidth}")
    
    # Convert to signed using two's complement
    sign_bit = 1 << (bitwidth - 1)
    if unsigned_value & sign_bit:
        # Negative number
        signed_value = unsigned_value - (1 << bitwidth)
        is_negative = True
    else:
        # Positive number
        signed_value = unsigned_value
        is_negative = False
    
    # Format outputs
    hex_str = f"0x{unsigned_value:0{(bitwidth + 3) // 4}x}"
    binary_str = f"0b{unsigned_value:0{bitwidth}b}"
    
    return {
        "unsigned": unsigned_value,
        "signed": signed_value,
        "hex": hex_str,
        "binary": binary_str,
        "is_negative": is_negative,
    }

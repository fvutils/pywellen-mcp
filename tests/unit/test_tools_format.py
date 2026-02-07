"""Tests for value formatting tools."""

import pytest
from pywellen_mcp.tools_format import format_value, format_as_signed


@pytest.mark.asyncio
class TestFormatValue:
    """Tests for format_value tool."""
    
    async def test_hex_to_decimal(self):
        """Test converting hex to decimal."""
        result = await format_value(
            value="0xFF",
            from_format="auto",
            to_format="decimal",
        )
        
        assert result["original"] == "0xFF"
        assert result["formatted"] == "255"
        assert result["numeric"] == 255
        assert result["format"] == "decimal"
    
    async def test_decimal_to_hex(self):
        """Test converting decimal to hex."""
        result = await format_value(
            value="255",
            from_format="auto",
            to_format="hex",
        )
        
        assert result["numeric"] == 255
        assert result["formatted"] == "0xff"
    
    async def test_binary_to_hex(self):
        """Test converting binary to hex."""
        result = await format_value(
            value="0b11111111",
            from_format="auto",
            to_format="hex",
        )
        
        assert result["numeric"] == 255
        assert result["formatted"] == "0xff"
    
    async def test_hex_to_binary(self):
        """Test converting hex to binary."""
        result = await format_value(
            value="0xF",
            from_format="auto",
            to_format="binary",
        )
        
        assert result["numeric"] == 15
        assert result["formatted"] == "0b1111"
    
    async def test_decimal_to_octal(self):
        """Test converting decimal to octal."""
        result = await format_value(
            value="64",
            from_format="auto",
            to_format="octal",
        )
        
        assert result["numeric"] == 64
        assert result["formatted"] == "0o100"
    
    async def test_with_bitwidth_padding(self):
        """Test formatting with bitwidth padding."""
        result = await format_value(
            value="0xF",
            to_format="binary",
            bitwidth=8,
        )
        
        assert result["formatted"] == "0b00001111"
    
    async def test_hex_padding(self):
        """Test hex formatting with padding."""
        result = await format_value(
            value="15",
            to_format="hex",
            bitwidth=16,
        )
        
        # Should pad to 4 hex digits (16 bits)
        assert result["formatted"] == "0x000f"
    
    async def test_auto_detect_hex(self):
        """Test auto-detection of hex format."""
        result = await format_value(
            value="0x1A2B",
            from_format="auto",
            to_format="decimal",
        )
        
        assert result["numeric"] == 0x1A2B
    
    async def test_auto_detect_binary(self):
        """Test auto-detection of binary format."""
        result = await format_value(
            value="0b1010",
            from_format="auto",
            to_format="decimal",
        )
        
        assert result["numeric"] == 10
    
    async def test_vcd_special_values(self):
        """Test handling VCD special values (x, z)."""
        result = await format_value(
            value="01xz",
            from_format="auto",
            to_format="hex",
        )
        
        # Should handle by converting x/z to 0
        assert result["numeric"] is not None
    
    async def test_non_numeric_passthrough(self):
        """Test non-numeric values pass through unchanged."""
        result = await format_value(
            value="invalid_xyz",
            from_format="auto",
            to_format="hex",
        )
        
        assert result["formatted"] == "invalid_xyz"
        assert result["numeric"] is None
    
    async def test_explicit_format(self):
        """Test with explicit from_format."""
        result = await format_value(
            value="FF",
            from_format="hex",
            to_format="decimal",
        )
        
        assert result["numeric"] == 255


@pytest.mark.asyncio
class TestFormatAsSigned:
    """Tests for format_as_signed tool."""
    
    async def test_positive_value(self):
        """Test converting positive value."""
        result = await format_as_signed(
            value="127",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 127
        assert result["signed"] == 127
        assert not result["is_negative"]
    
    async def test_negative_value(self):
        """Test converting negative value (MSB set)."""
        result = await format_as_signed(
            value="255",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 255
        assert result["signed"] == -1
        assert result["is_negative"]
    
    async def test_max_negative(self):
        """Test maximum negative value."""
        result = await format_as_signed(
            value="128",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 128
        assert result["signed"] == -128
        assert result["is_negative"]
    
    async def test_zero(self):
        """Test zero value."""
        result = await format_as_signed(
            value="0",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 0
        assert result["signed"] == 0
        assert not result["is_negative"]
    
    async def test_hex_input(self):
        """Test with hex input."""
        result = await format_as_signed(
            value="0x80",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 128
        assert result["signed"] == -128
        assert result["is_negative"]
    
    async def test_binary_input(self):
        """Test with binary input."""
        result = await format_as_signed(
            value="0b10000000",
            bitwidth=8,
        )
        
        assert result["unsigned"] == 128
        assert result["signed"] == -128
    
    async def test_16bit_value(self):
        """Test with 16-bit value."""
        result = await format_as_signed(
            value="0x8000",
            bitwidth=16,
        )
        
        assert result["unsigned"] == 32768
        assert result["signed"] == -32768
        assert result["is_negative"]
    
    async def test_output_formats(self):
        """Test that output includes all formats."""
        result = await format_as_signed(
            value="200",
            bitwidth=8,
        )
        
        assert "hex" in result
        assert "binary" in result
        assert result["hex"].startswith("0x")
        assert result["binary"].startswith("0b")
    
    async def test_invalid_value_error(self):
        """Test error handling for invalid value."""
        with pytest.raises(ValueError):
            await format_as_signed(
                value="invalid",
                bitwidth=8,
            )
    
    async def test_overflow_error(self):
        """Test error when value exceeds bitwidth."""
        with pytest.raises(ValueError):
            await format_as_signed(
                value="256",
                bitwidth=8,
            )
    
    async def test_explicit_decimal_input(self):
        """Test with explicit decimal input format."""
        result = await format_as_signed(
            value="240",
            bitwidth=8,
            input_format="decimal",
        )
        
        assert result["unsigned"] == 240
        assert result["signed"] == -16

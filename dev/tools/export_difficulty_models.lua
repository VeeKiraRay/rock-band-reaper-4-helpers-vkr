-- Export the modern helper's generated Lua difficulty models as Python data.
--
-- Usage:
--   lua dev/tools/export_difficulty_models.lua INPUT.lua OUTPUT.py
--
-- INPUT.lua is the modern project's lib/reaper_difficulty_models.lua. The
-- generated Python file is deterministic and contains data only.

local input, output = arg[1], arg[2]
if not input or not output then
    io.stderr:write('usage: export_difficulty_models.lua INPUT.lua OUTPUT.py\n')
    os.exit(2)
end

dofile(input)

local function quoted(value)
    return string.format('%q', value)
end

local function is_array(value)
    local count, highest = 0, 0
    for key in pairs(value) do
        if type(key) ~= 'number' or key < 1 or key % 1 ~= 0 then return false end
        count = count + 1
        if key > highest then highest = key end
    end
    -- Model vectors are never empty. Treat an empty Lua table as a mapping so
    -- fields such as an instrument's empty correlation table still provide
    -- Python's dictionary interface to the explanation layer.
    return count > 0 and count == highest
end

local function sorted_keys(value)
    local keys = {}
    for key in pairs(value) do keys[#keys + 1] = key end
    table.sort(keys, function(a, b)
        if type(a) == type(b) then return a < b end
        return type(a) < type(b)
    end)
    return keys
end

local function write_value(handle, value, indent)
    local kind = type(value)
    if kind == 'string' then
        handle:write(quoted(value))
    elseif kind == 'number' then
        handle:write(string.format('%.17g', value))
    elseif kind == 'boolean' then
        handle:write(value and 'True' or 'False')
    elseif kind == 'nil' then
        handle:write('None')
    elseif kind == 'table' then
        local next_indent = indent .. '    '
        if is_array(value) then
            handle:write('[\n')
            for index = 1, #value do
                handle:write(next_indent)
                write_value(handle, value[index], next_indent)
                handle:write(',\n')
            end
            handle:write(indent .. ']')
        else
            handle:write('{\n')
            for _, key in ipairs(sorted_keys(value)) do
                handle:write(next_indent)
                write_value(handle, key, next_indent)
                handle:write(': ')
                write_value(handle, value[key], next_indent)
                handle:write(',\n')
            end
            handle:write(indent .. '}')
        end
    else
        error('cannot export Lua value of type ' .. kind)
    end
end

local handle, err = io.open(output, 'wb')
if not handle then error(err) end
handle:write('"""Frozen calibrated difficulty models.\n\n')
handle:write('Generated from the modern helper; do not edit by hand.\n')
handle:write('Python 2.7 compatible.\n"""\n\n')
handle:write('from __future__ import unicode_literals\n\n')
handle:write('RB_DIFFICULTY_MODELS_SCHEMA = ')
write_value(handle, RB_DIFFICULTY_MODELS_SCHEMA, '')
handle:write('\nRB_DIFFICULTY_MODELS_CSV_FINGERPRINT = ')
write_value(handle, RB_DIFFICULTY_MODELS_CSV_FINGERPRINT, '')
handle:write('\nRB_DIFFICULTY_MODEL_ORDER = ')
write_value(handle, RB_DIFFICULTY_MODEL_ORDER, '')
handle:write('\nRB_DIFFICULTY_MODELS = ')
write_value(handle, RB_DIFFICULTY_MODELS, '')
handle:write('\n')
handle:close()

io.stdout:write('Exported ' .. tostring(#RB_DIFFICULTY_MODEL_ORDER) ..
                ' difficulty models to ' .. output .. '\n')

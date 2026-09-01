-- Export the modern helper's pure Lua genre tables as Python 2-compatible
-- data modules for the REAPER 4.20 port.
--
-- Usage:
--   lua dev/tools/export_genre_tables.lua <modern-module-dir> <python-module-dir>

local source_dir = assert(arg[1], 'modern module directory is required')
local target_dir = assert(arg[2], 'Python module directory is required')

local sep = package.config:sub(1, 1)
local function join(a, b)
    if a:sub(-1) == sep then return a .. b end
    return a .. sep .. b
end

dofile(join(source_dir, 'metadata_genres.lua'))
dofile(join(source_dir, 'metadata_genres_ext.lua'))

local function py_string(value)
    local escaped = value:gsub('[%z\1-\31\\"]', function(ch)
        local map = {
            ['\\'] = '\\\\', ['"'] = '\\"', ['\n'] = '\\n',
            ['\r'] = '\\r', ['\t'] = '\\t', ['\b'] = '\\b',
            ['\f'] = '\\f',
        }
        return map[ch] or string.format('\\x%02x', string.byte(ch))
    end)
    return '"' .. escaped .. '"'
end

local function is_array(value)
    if type(value) ~= 'table' then return false end
    local count, maximum = 0, 0
    for key in pairs(value) do
        if type(key) ~= 'number' or key < 1 or key % 1 ~= 0 then
            return false
        end
        count = count + 1
        if key > maximum then maximum = key end
    end
    return count == maximum
end

local function serialize(value, depth)
    depth = depth or 0
    local kind = type(value)
    if kind == 'string' then return py_string(value) end
    if kind == 'number' then return tostring(value) end
    if kind == 'boolean' then return value and 'True' or 'False' end
    if kind == 'nil' then return 'None' end
    assert(kind == 'table', 'unsupported value type: ' .. kind)

    local indent = string.rep('    ', depth)
    local child_indent = string.rep('    ', depth + 1)
    local lines = {}
    if is_array(value) then
        if #value == 0 then return '[]' end
        for i = 1, #value do
            lines[#lines + 1] = child_indent .. serialize(value[i], depth + 1) .. ','
        end
        return '[\n' .. table.concat(lines, '\n') .. '\n' .. indent .. ']'
    end

    local keys = {}
    for key in pairs(value) do keys[#keys + 1] = key end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    if #keys == 0 then return '{}' end
    for _, key in ipairs(keys) do
        lines[#lines + 1] = child_indent .. py_string(tostring(key)) .. ': ' ..
            serialize(value[key], depth + 1) .. ','
    end
    return '{\n' .. table.concat(lines, '\n') .. '\n' .. indent .. '}'
end

local function write_module(filename, modern_source, assignments)
    local path = join(target_dir, filename)
    local handle = assert(io.open(path, 'wb'))
    handle:write('"""Generated genre data.\n\n')
    handle:write('Modern counterpart: rock_band_general_helper_vkr/' .. modern_source .. '\n')
    handle:write('Regenerate with dev/tools/export_genre_tables.lua.\n')
    handle:write('Python 2.7 compatible.\n"""\n\n')
    for _, assignment in ipairs(assignments) do
        handle:write(assignment[1] .. ' = ' .. serialize(assignment[2], 0) .. '\n\n')
    end
    handle:close()
end

write_module('metadata_genres.py', 'metadata_genres.lua', {
    { 'RB3_GENRE_ORDER', RB3_GENRE_ORDER },
    { 'RB3_GENRES', RB3_GENRES },
})

write_module('metadata_genres_ext.py', 'metadata_genres_ext.lua', {
    { 'GENRE_FAMILY_ORDER', GENRE_FAMILY_ORDER },
    { 'GENRE_FAMILIES', GENRE_FAMILIES },
    { 'EXTENDED_GENRES', EXTENDED_GENRES },
})

print(string.format(
    'Exported %d supported genres and %d extended entries.',
    #RB3_GENRE_ORDER, #EXTENDED_GENRES))


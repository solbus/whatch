local mp = require "mp"
local options = require "mp.options"

local o = {
    log_path = "",
}

options.read_options(o, "whatch_watch")

local function append_path()
    if not o.log_path or o.log_path == "" then
        return
    end
    local path = mp.get_property("path")
    if not path or path == "" then
        return
    end
    local file = io.open(o.log_path, "a")
    if file then
        file:write(path .. "\n")
        file:close()
    end
end

mp.register_event("file-loaded", append_path)

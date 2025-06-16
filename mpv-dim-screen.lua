require 'mp.msg'
local utils = require 'mp.utils'

local original_brightness

function dim_screen()
    local target_output = mp.get_opt("screen_brightness_output")
    local brightness = mp.get_opt("screen_brightness_value")
    if target_output == nil or brightness == nil then
        mp.msg.log("error", "screen_brightess_output and screen_brightness_value script-opts should be set")
    else
        local r = mp.command_native({name = "subprocess",
                                     playback_only = false,
                                     capture_stdout = true,
                                     args = {"kscreen-doctor", "-j"}})
        local data = utils.parse_json(r.stdout)
        for i,output in ipairs(data["outputs"]) do
            if output["name"] == target_output then
                original_brightness = output["sdr-brightness"]
                mp.msg.log("info", "Original brightness is " .. original_brightness .. ".")
            end
        end
        if original_brightness == nil then
            mp.msg.log("error", "Failed to get original brightness.")
        else
            mp.msg.log("info", "Setting brightness to " .. brightness .. ".")
            mp.commandv("run", "kscreen-doctor", "output." .. target_output .. ".sdr-brightness." .. brightness)
        end
    end
end

function bright_screen()
    local target_output = mp.get_opt("screen_brightness_output")
    if target_output == nil or original_brightness == nil then
        mp.msg.log("error", "original output or original brightness aren't known")
    else
        mp.msg.log("info", "Restoring brightness to " .. original_brightness .. ".")
        mp.commandv("run", "kscreen-doctor", "output." .. target_output .. ".sdr-brightness." .. original_brightness)
    end
end

mp.register_event("shutdown", bright_screen)
dim_screen()

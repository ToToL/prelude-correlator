-- Copyright (C) 2009 INL <inl@inl.fr>
-- Copyright (C) 2009 S. Tricaud <stricaud@inl.fr>
-- Copyright (C) 2009 PreludeIDS Technologies <info@prelude-ids.com>
-- All Rights Reserved.
--
-- This file is part of the Prelude-Correlator program.
--
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2, or (at your option)
-- any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program; see the file COPYING.  If not, write to
-- the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.

-- IMPORTANT. READ ME!
-- This script checks against the Dshield (www.dshield.org) database
-- for source IP addresses matching it.
-- To have this correlation rule working:
--   * you need to set up a mirror fetching
--     http://www.dshield.org/ipsascii.html?limit=10000 once a week.
--   * save this file under /etc/prelude-correlator/ipascii.html
--
-- If you want to set up a dshield mirror for IP and ports list,
-- you can use this Perl script: http://www.wallinfire.net/files/dshield-mirror



function normalize_ip(ipaddr)
        quads = string.split(ipaddr, ".")
        return string.format("%.3d.%.3d.%.3d.%.3d", quads[1], quads[2], quads[3], quads[4])
end



function dshield(INPUT)

io.input("/etc/prelude-correlator/ipsascii.html")

local result = INPUT:match("alert.source(*).node.address(*).address", "(.+)",
                           "alert.target(*).node.address(*).address", "(.+)");
if result then
        for i, source in ipairs(result[1]) do
                normalized_ip = normalize_ip(source)
                for line in io.lines() do
                        val = string.split(line, "\t")
                        if not string.find(val[0],"^#.*") then
                                if string.find(val[0], normalized_ip) then
                                        local ctx = Context.update("DSHIELD_DB_" .. source, { threshold = 1 })
                                        ctx:set("alert.source(>>)", INPUT:getraw("alert.source"))
                                        ctx:set("alert.target(>>)", INPUT:getraw("alert.target"))
                                        ctx:set("alert.correlation_alert.alertident(>>).alertident", INPUT:getraw("alert.messageid"))
                                        ctx:set("alert.correlation_alert.alertident(-1).analyzerid", INPUT:getAnalyzerid())
                                        ctx:set("alert.classification.text", "IP source matching Dshield database")
                                        ctx:set("alert.correlation_alert.name", "IP source matching Dshield database")
                                        ctx:set("alert.assessment.impact.description", "Dshield gather IP addresses taged from firewall logs drops")
                                        ctx:set("alert.assessment.impact.severity", "high")
                                        ctx:alert()
                                        ctx:del()
                                end
                        end
                end
        end -- for i, source in ipairs(result[1]) do
end -- if result then

end -- function dshield_match(INPUT)


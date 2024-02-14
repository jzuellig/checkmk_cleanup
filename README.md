## Checkmk Ruleset Cleanup
This script removes hosts out of the conditions of all rules, if they do not exist in the Setup.

If all hosts from one rule have been removed, the rule will be deleted.

**Regex Matches are not proccess**

### Planed Features
- [ ] Check if host is under folder path and if not remove it too
- [ ] Check if regex matches any host 

---
id: "202602251636"
tags:
  - 📝
up: "[[00 - Daily Workflow]]"
topics:
---
# [[Daily Note]]
# <% tp.date.now("dddd, MMMM DD, YYYY") %>

<%*
// Debug: Check if the function exists
if (tp.user.getOrthodoxData) {
    console.log("ORTHODOX DEBUG: Script found in tp.user");
} else {
    console.error("ORTHODOX DEBUG: Script NOT FOUND in tp.user. Check folder settings.");
}

const data = await tp.user.getOrthodoxData();
// This will force the data into the scope
const liturgicalDay = data.liturgicalDay;
const fastInfo = data.fastInfo;
const readingsText = data.readingsText;
%>

## Daily Praxis

**Liturgical:** <% liturgicalDay %>
**Fast:** <% fastInfo %>

**Prayer rule:**
- Morning prayers:
- Scripture reading:
- Evening prayers:

**📖 Scripture:**
- Lectionary: <% readingsText %>
- Psalm: 
- **From memory:** ---


---

## What Needs Doing Today
*Plugin rolls over unchecked tasks to here*

### Today's Tasks
- [ ] 

---

## Quick Notes
*Jot things down as they come up during the day*

- 

---

## Church/Class Links
*If you went to liturgy, class, or processed spiritual reading*

- 

---

## Evening (Optional - only when you can)
*Don't beat yourself up if you skip this section*

**One thing worth remembering about today:**

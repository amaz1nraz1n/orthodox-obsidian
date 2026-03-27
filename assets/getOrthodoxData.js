console.log("ORTHODOX DEBUG: Script file loaded by Obsidian");

async function getOrthodoxData() {
  console.log("ORTHODOX DEBUG: Function getOrthodoxData called");
  let result = {
    liturgicalDay: "Data not found",
    fastInfo: "Data not found",
    readingsText: "Data not found",
  };

  try {
    const fetchOptions = {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      },
    };

    // 1. Get Bearer Token
    const tokenOptions = {
      url: "https://www.antiochian.org/connect/token",
      method: "POST",
      body: "client_id=antiochian_api&client_secret=TAxhx@9tH(l%5EMgQ9FWE8%7DT@NWUT9U)&grant_type=client_credentials",
      headers: {
        ...fetchOptions.headers,
        "Content-Type": "application/x-www-form-urlencoded",
      },
    };

    console.log("ORTHODOX DEBUG: Fetching Bearer token");
    const tokenResponse = await requestUrl(tokenOptions);
    let tokenData;
    if (tokenResponse.json) {
      tokenData = tokenResponse.json;
    } else {
      tokenData = JSON.parse(tokenResponse.text);
    }

    const token = tokenData.access_token;
    if (!token) {
      console.error("ORTHODOX DEBUG: Failed to fetch API token.");
      return result;
    }

    // 2. Fetch Liturgical Data for today (LiturgicalDay/0)
    const apiOptions = {
      url: "https://www.antiochian.org/api/antiochian/LiturgicalDay/0",
      method: "GET",
      headers: {
        ...fetchOptions.headers,
        Authorization: `Bearer ${token}`,
      },
    };

    console.log("ORTHODOX DEBUG: Fetching LiturgicalDay/0 data");
    const apiResponse = await requestUrl(apiOptions);
    let apiData;
    if (apiResponse.json) {
      apiData = apiResponse.json;
    } else {
      apiData = JSON.parse(apiResponse.text);
    }

    const dayData = apiData.liturgicalDay;

    if (dayData) {
      if (dayData.feastDayTitle) {
        result.liturgicalDay = dayData.feastDayTitle;
        if (dayData.feastDayDescription) {
          result.liturgicalDay += " - " + dayData.feastDayDescription;
        }
      }

      if (dayData.fastDesignation) {
        result.fastInfo = dayData.fastDesignation;
      }


      // 3. Process Readings dynamically
      // API typically returns reading1Title, reading2Title, etc.
      let readingsNodes = [];
      for (let i = 1; i <= 10; i++) {
        const readingTitle = dayData[`reading${i}Title`];
        if (readingTitle) {
          readingsNodes.push(readingTitle);
        }
      }

      if (readingsNodes.length > 0) {
        result.readingsText = readingsNodes
          .map((t) => t.trim())
          .filter((t) => t)
          .map((t) => {
            let segments = t.split(";").map((s) => s.trim());
            let formattedSegments = [];
            let lastBook = "";

            for (let segment of segments) {
              // Match [Book] [Chapter]:[Verses] (Book is optional, inheriting from last one)
              // Verses can include hyphens, commas, and spaces
              let match = segment.match(/^(?:(.+?)\s+)?(\d+)\s*:\s*([\d\-, ]+)/i);
              if (!match) {
                formattedSegments.push(segment);
                continue;
              }

              let fullBook = (match[1] || "").trim();
              let book = fullBook.toUpperCase();

              // Heritage/Inheritance for book name
              if (!book && lastBook) {
                book = lastBook;
                fullBook = lastBook;
              }
              lastBook = book;

              // Extract number prefix if present
              let roman = "";
              if (/\bFIRST\b|(?:\b|^)I\b/.test(book)) roman = "I ";
              else if (/\bSECOND\b|(?:\b|^)II\b/.test(book)) roman = "II ";
              else if (/\bTHIRD\b|(?:\b|^)III\b/.test(book)) roman = "III ";
              else if (/\bFOURTH\b|(?:\b|^)IV\b/.test(book)) roman = "IV ";

              // Clean the book name
              let cleanedBook = book
                .replace(/ST\.\s+PAUL'S/i, "")
                .replace(/ST\.\s+PETER'S/i, "PETER")
                .replace(/ST\.\s+JUDE'S/i, "JUDE")
                .replace(/ST\.\s+JAMES'/i, "JAMES")
                .replace(/ST\.\s+JOHN'S/i, "JOHN")
                .replace(/ACTS\s+OF\s+THE\s+APOSTLES/i, "ACTS")
                .replace(/\b(FIRST|SECOND|THIRD|FOURTH|I|II|III|IV)\b/g, "")
                .replace(
                  /\b(LETTER|UNIVERSAL|CATHOLIC|TO THE|TO|THE|OF ST\.)\b/g,
                  "",
                )
                .replace(/\s+/g, " ")
                .trim();

              // Specific Orthodox mappings
              if (cleanedBook === "SAMUEL" || cleanedBook === "KINGS")
                cleanedBook = "Kingdoms";
              if (cleanedBook === "PARALIPOMENON") cleanedBook = "Chronicles";

              // Title case the book name
              cleanedBook =
                cleanedBook.charAt(0).toUpperCase() +
                cleanedBook.slice(1).toLowerCase();

              // Re-apply Roman numeral prefix (strip for single-book cases)
              const singleLetterBooks = [
                "Hebrews",
                "James",
                "Jude",
                "Acts",
                "Romans",
                "Galatians",
                "Ephesians",
                "Philippians",
                "Colossians",
                "Titus",
                "Philemon",
                "Revelation",
              ];
              if (singleLetterBooks.includes(cleanedBook)) {
                roman = "";
              }

              let finalBook = (roman + cleanedBook).trim();
              let chapter = match[2];
              let versesFull = match[3];

              // Split non-contiguous verse ranges (separated by commas)
              let verseGroups = versesFull.split(",").map((v) => v.trim());
              for (let vRange of verseGroups) {
                if (!vRange) continue;
                // First verse in this specific range for anchor link
                let vMatch = vRange.match(/\d+/);
                if (!vMatch) continue;
                let startV = vMatch[0];

                // Link target uses cleaned book name
                // Display text also includes the cleaned book name for consistency
                formattedSegments.push(
                  `[[${finalBook} ${chapter}#v${startV}|${finalBook} ${chapter}:${vRange}]]`,
                );
              }
            }
            return formattedSegments.join(", ");
          })
          .join(", ");
      }
    }
  } catch (e) {
    console.error("Scraper Error:", e);
  }
  return result;
}
module.exports = getOrthodoxData;

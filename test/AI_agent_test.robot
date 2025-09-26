# *** Settings ***
# Library           RPA.Excel.Files
# Library           RequestsLibrary
# Library           Collections
# Library           BuiltIn
# Library           String


# Suite Setup       Read Excel Data
# Suite Teardown    Close Workbook

# *** Variables ***
# ${EXCEL_FILE}     test_data1.xlsx
# ${AI_URL}         http://localhost:8502

# *** Keywords ***
# Read Excel Data
#     Open Workbook    ${EXCEL_FILE}
#     ${rows}=    Read Worksheet As Table    header=True
#     Set Suite Variable    ${QUESTIONS}    ${rows}

# Ask AI Agent
#     [Arguments]    ${question}
#     ${payload}=    Create Dictionary    question=${question}
#     Create Session    ai    ${AI_URL}
#     ${response}=   POST On Session    ai    /predict    json=${payload}
#     Should Be Equal As Integers    ${response.status_code}    200
#     ${json_data}=  Convert To Dictionary    ${response.json()}
#     ${answer}=     Get From Dictionary    ${json_data}    answer
#     RETURN    ${answer}

# # Old Normalize Text is kept, can be used for strict character comparison
# Normalize Text
#     [Arguments]    ${text}
#     ${text_lower}=    Convert To Lowercase    ${text}
#     ${letters_only}=    Replace String Using Regexp    ${text_lower}    [^a-zA-Z]+    ${EMPTY}
#     RETURN    ${letters_only}

# # Robust Compare AI Response using normalized substring match (Option 1)
# # Compare only key terms instead of full paragraph
# Compare AI Response
#     [Arguments]    ${expected_text}    ${actual_text}
#     ${expected_norm}=    Convert To Lowercase    ${expected_text}
#     ${actual_norm}=      Convert To Lowercase    ${actual_text}
#     # Split expected keywords by comma and check each exists in AI answer
#     @{keywords}=    Split String    ${expected_norm}    ,
#     FOR    ${kw}    IN    @{keywords}
#         ${kw_strip}=    Strip String    ${kw}
#         Run Keyword And Ignore Error    Should Contain    ${actual_norm}    ${kw_strip}
#     END


# Run AI Question
#     [Arguments]    ${question}    ${expected}
#     ${actual}=    Ask AI Agent    ${question}
#     Log To Console    =========================
#     Log To Console    Question: ${question}
#     Log To Console    AI Answer: ${actual}
#     Compare AI Response    ${expected}    ${actual}

# *** Test Cases ***
# Generate AI Questions From Excel
#     FOR    ${row}    IN    @{QUESTIONS}
#         ${question}=    Get From Dictionary    ${row}    Question
#         ${expected}=    Get From Dictionary    ${row}    Expected Response
#         Log To Console    Running test for question: ${question}
#         Run AI Question    ${question}    ${expected}
#     END


# *** Settings ***
# Library           RPA.Excel.Files
# Library           RequestsLibrary
# Library           Collections
# Library           BuiltIn
# Library           String

# Suite Setup       Read Excel Data
# Suite Teardown    Show Accuracy

# *** Variables ***
# ${EXCEL_FILE}     test_data1.xlsx
# ${AI_URL}         http://localhost:8502
# ${TOTAL}=         0
# ${PASSED}=        0

# *** Keywords ***
# Read Excel Data
#     Open Workbook    ${EXCEL_FILE}
#     ${rows}=    Read Worksheet As Table    header=True
#     Set Suite Variable    ${QUESTIONS}    ${rows}

# Ask AI Agent
#     [Arguments]    ${question}
#     ${payload}=    Create Dictionary    question=${question}
#     Create Session    ai    ${AI_URL}
#     ${response}=   POST On Session    ai    /predict    json=${payload}
#     Should Be Equal As Integers    ${response.status_code}    200
#     ${json_data}=  Convert To Dictionary    ${response.json()}
#     ${answer}=     Get From Dictionary    ${json_data}    answer
#     RETURN    ${answer}

# Compare AI Response
#     [Arguments]    ${expected_text}    ${actual_text}
#     ${expected_norm}=    Convert To Lowercase    ${expected_text}
#     ${actual_norm}=      Convert To Lowercase    ${actual_text}
#     @{keywords}=    Split String    ${expected_norm}    ,
#     ${all_match}=    Set Variable    True
#     FOR    ${kw}    IN    @{keywords}
#         ${kw_strip}=    Strip String    ${kw}
#         ${res}=    Run Keyword And Return Status    Should Contain    ${actual_norm}    ${kw_strip}
#         Run Keyword If    not ${res}    Set Variable    ${all_match}    False
#     END
#     RETURN    ${all_match}

# Run AI Question
#     [Arguments]    ${question}    ${expected}
#     ${actual}=    Ask AI Agent    ${question}
#     Log To Console    =========================
#     Log To Console    Question: ${question}
#     Log To Console    AI Answer: ${actual}
#     ${match}=    Compare AI Response    ${expected}    ${actual}
#     ${TOTAL}=    Evaluate    ${TOTAL} + 1
#     Set Suite Variable    ${TOTAL}
#     Run Keyword If    ${match}    Increment Pass Count

# Increment Pass Count
#     ${PASSED}=    Evaluate    ${PASSED} + 1
#     Set Suite Variable    ${PASSED}

# Show Accuracy
#     ${accuracy}=    Evaluate    (${PASSED} / ${TOTAL}) * 100
#     Log To Console    ---------------------------------
#     Log To Console    Total Questions: ${TOTAL}
#     Log To Console    Passed: ${PASSED}
#     Log To Console    Accuracy: ${accuracy}%
#     Log To Console    ---------------------------------

# *** Test Cases ***
# Generate AI Questions From Excel
#     FOR    ${row}    IN    @{QUESTIONS}
#         ${question}=    Get From Dictionary    ${row}    Question
#         ${expected}=    Get From Dictionary    ${row}    Expected Response
#         Log To Console    Running test for question: ${question}
#         Run AI Question    ${question}    ${expected}
#     END


*** Settings ***
Library           RPA.Excel.Files
Library           RequestsLibrary
Library           Collections
Library           BuiltIn
Library           String
Library           OperatingSystem
Library           ./GPTVerifier.py

Suite Setup       Read Questions
Suite Teardown    Run Keywords    Show Accuracy    AND    Generate HTML Report


*** Variables ***
${EXCEL_FILE}     ./test/test_data1.xlsx
${AI_URL}         http://localhost:8502
${TOTAL}          0
${PASSED}         0
${accuracy}       0
${QUESTIONS}      None

*** Keywords ***
Read Questions
    Open Workbook    ${EXCEL_FILE}
    ${rows}=    Read Worksheet As Table    header=True
    Set Suite Variable    ${QUESTIONS}    ${rows}

Ask AI Agent
    [Arguments]    ${question}
    ${payload}=    Create Dictionary    question=${question}
    Create Session    ai    ${AI_URL}
    ${response}=   POST On Session    ai    /predict    json=${payload}
    Should Be Equal As Integers    ${response.status_code}    200
    ${json_data}=  Convert To Dictionary    ${response.json()}
    ${answer}=     Get From Dictionary    ${json_data}    answer
    Delete All Sessions
    [Return]    ${answer}

Run AI Question
    [Arguments]    ${question}

    # Run each question safely, ignoring errors to continue test
    ${result}=    Run Keyword And Ignore Error    _Run AI Question Internal    ${question}
    # ${result} = [status, return value], e.g. ['PASS', value] or ['FAIL', error message]
    Run Keyword If    '${result[0]}'=='FAIL'    Log To Console    ERROR processing question "${question}": ${result[1]}

_Run AI Question Internal
    [Arguments]    ${question}
    ${ai_answer}=    Ask AI Agent    ${question}
    Log To Console    ==============================
    Log To Console    Question: ${question}
    Log To Console    AI Answer: ${ai_answer}

    ${score}    ${pass}    ${feedback}=    Verify Answer    ${question}    ${ai_answer}

    # Convert score to percentage
    ${score_percent}=    Evaluate    round(${score} * 100)

    # Convert True/False to Pass/Fail
    ${status}=    Run Keyword If    ${pass}    Set Variable    Pass    ELSE    Set Variable    Fail

    Log To Console    Score: ${score_percent}%, Status: ${status}, Feedback: ${feedback}

    ${TOTAL}=    Evaluate    ${TOTAL} + 1
    Set Suite Variable    ${TOTAL}    ${TOTAL}

    Run Keyword If    ${pass}    Increment Pass Count

    # Save result to CSV even if question fails
    Append To File    report.csv    ${question},${ai_answer},${score_percent}%,${status},${feedback}

Increment Pass Count
    ${PASSED}=    Evaluate    ${PASSED} + 1
    Set Suite Variable    ${PASSED}    ${PASSED}

Show Accuracy
    Run Keyword If    ${TOTAL} > 0
    ...    ${accuracy}=    Evaluate    round((${PASSED} / ${TOTAL}) * 100, 2)
    ...    ELSE    ${accuracy}=    Set Variable    0
    Set Suite Variable    ${accuracy}    ${accuracy}
    Set Suite Variable    ${TOTAL}       ${TOTAL}
    Set Suite Variable    ${PASSED}      ${PASSED}
    Log To Console    ---------------------------------
    Log To Console    Total Questions: ${TOTAL}
    Log To Console    Passed: ${PASSED}
    ${failed}=    Evaluate    ${TOTAL} - ${PASSED}
    Log To Console    Failed: ${failed}
    Log To Console    Accuracy: ${accuracy}%
    Log To Console    ---------------------------------

Generate HTML Report
    ${failed}=    Evaluate    ${TOTAL} - ${PASSED}
    ${html}=      Catenate    SEPARATOR=\n
    ...           <html><head><style>
    ...           table {border-collapse: collapse; width: 100%;}
    ...           th, td {border: 1px solid black; padding: 8px; text-align: left;}
    ...           th {background-color: #f2f2f2;}
    ...           .pass {background-color: #c8e6c9;}
    ...           .fail {background-color: #ffcdd2;}
    ...           </style></head><body>
    ...           <h2>AI Agent Test Report</h2>
    ...           <h3>Summary</h3>
    ...           <table>
    ...           <tr><th>Total Questions</th><th>Passed</th><th>Failed</th><th>Accuracy</th></tr>
    ...           <tr><td>${TOTAL}</td><td>${PASSED}</td><td>${failed}</td><td>${accuracy}%</td></tr>
    ...           </table><br>
    ...           <h3>Details</h3>
    ...           <table>
    ...           <tr><th>Question</th><th>AI Answer</th><th>Score</th><th>Result</th><th>Feedback</th></tr>

    ${lines}=    Get File    report.csv
    ${rows}=     Split To Lines    ${lines}

    FOR    ${row}    IN    @{rows[1:]}
        ${cols}=    Split String    ${row}    ,
        ${q}=       Set Variable    ${cols[0]}
        ${a}=       Set Variable    ${cols[1]}
        ${s}=       Set Variable    ${cols[2]}
        ${r}=       Set Variable    ${cols[3]}
        ${f}=       Set Variable    ${cols[4]}
        ${class}=   Run Keyword If    '${r}'=='Pass'    Set Variable    pass    ELSE    Set Variable    fail
        ${html}=    Catenate    SEPARATOR=\n    ${html}    <tr class="${class}"><td>${q}</td><td>${a}</td><td>${s}</td><td>${r}</td><td>${f}</td></tr>
    END

    ${html}=    Catenate    SEPARATOR=\n    ${html}    </table></body></html>
    Create File    report.html    ${html}
    Log To Console    HTML report generated: report.html

*** Test Cases ***
Evaluate All Questions
    # Initialize CSV
    Create File    report.csv
    Append To File    report.csv    Question,AI Answer,Score,Result,Feedback

    FOR    ${row}    IN    @{QUESTIONS}
        ${question}=    Get From Dictionary    ${row}    Question
        Run AI Question    ${question}
    END

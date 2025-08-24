# 🚀 Quick Start Guide: Interactive Conversational Demo

This guide helps testers quickly run and test the 5-step conversational query analysis flow with human interaction.

## 🔄 Getting the Code

### Option 1: Fresh Clone (New Users)
If you don't have the project yet:
```bash
# Clone the repository
git clone https://github.com/simkimsia/genai-202504-team-1.git

# Navigate to the project
cd genai-202504-team-1

# Switch to the query-analysis branch
git checkout query-analysis
```

### Option 2: Update Existing Project
If you already have the project:
```bash
# Navigate to your existing project directory
cd /path/to/your/genai-202504-team-1

# Fetch latest changes from remote
git fetch origin

# Switch to and update the query-analysis branch
git checkout query-analysis
git pull origin query-analysis
```

### Option 3: Download ZIP (No Git Required)
1. Go to: https://github.com/simkimsia/genai-202504-team-1
2. Click the green **"Code"** button
3. Select **"Download ZIP"**
4. Extract the ZIP file
5. Open terminal and navigate to the extracted folder

## 📋 Prerequisites

1. **Ollama must be running** with a model installed:
   ```bash
   # Check if Ollama is running
   ollama list
   
   # If not, start Ollama and pull a model
   ollama pull llama3.2
   ```

2. **Python environment** with dependencies:
   ```bash
   # From project root directory (genai-202504-team-1)
   pip install -r requirements-query-analysis.txt
   ```

## 🎯 Running the Demo

```bash
# Make sure you're in the project root directory
cd genai-202504-team-1

# Run the interactive demo
python tests/query_analyzer/interactive_conversational_demo.py
```

### ⚠️ Important Notes
- **Make sure you're on the `query-analysis` branch** - the demo won't work on other branches
- **Verify your location**: Run `pwd` to check you're in the right directory
- **Check branch**: Run `git branch` to confirm you're on `query-analysis`

## 🔧 Initial Setup (First Run)

When you start the demo, you'll configure the workflow:

### 1. **Choose Relevance Mode**
```
Choose relevance checking mode:
1. Two-stage (vocabulary + semantic)
2. Task-action-target (LLM-based) - Default
3. Disabled

Enter choice (1-3) [2]: 
```
- **Type 1** for two-stage mode (vocabulary + semantic)
- **Press Enter** for default task-action-target mode (better for action queries)
- **Type 3** to skip relevance checking

### 2. **Choose Rejection Mode** (if relevance enabled)
```
Choose rejection mode:
1. Hard (reject immediately)
2. Soft (continue with low confidence)
3. Score only (never reject)

Enter choice (1-3) [1]:
```
- **Press Enter** for hard rejection (recommended for testing)
- **Type 2** for soft rejection (processes but flags low confidence)

### 3. **Enable Clarification**
```
Enable interactive clarification?
(y/n) [y]:
```
- **Press Enter** to enable (recommended)
- **Type n** to disable clarification

### 4. **Select User Level**
```
Select user expertise level:
1. Novice
2. Experienced
3. Expert

Enter choice (1-3) [1]:
```
- **Press Enter** for Novice (gets simpler explanations)
- Higher levels get more technical details

## 🎮 Using the Demo

### Basic Commands

| Command | Action |
|---------|--------|
| **Any text** | Process as a query |
| **summary** | View session summary |
| **reset** | Start new session |
| **quit** or **exit** | End demo |

### Example Test Scenarios

#### 1. **Test Ambiguous Query (Clarification)**
```
Enter query: How do I fix it?
```
Expected flow:
- ✅ Step 1: Initial prompt received
- ✅ Step 2: Relevance check passed
- ✅ Step 3: Clarification questions appear
  - Answer the questions interactively
- ✅ Step 4: Intent analysis with context
- ✅ Step 5: Query enhancement

#### 2. **Test Irrelevant Query (Rejection)**
```
Enter query: What's the weather today?
```
Expected flow:
- ✅ Step 1: Initial prompt received
- ❌ Step 2: Relevance check failed
- Query rejected with explanation

#### 3. **Test Clear Technical Query**
```
Enter query: How to replace brake pads on a 2020 Honda Civic?
```
Expected flow:
- ✅ All 5 steps complete
- No clarification needed
- Full analysis with expansions and decompositions

#### 4. **Test Conversation Context**
```
Enter query: Tell me about diesel engines
Enter query: What about their maintenance?
```
Second query uses context from first ("their" = diesel engines)

## 📊 Understanding the Output

### Step Indicators
- ✅ **Green checkmark**: Step completed successfully
- ❌ **Red X**: Step failed
- ➖ **Dash**: Step skipped (not needed)
- ⚠️ **Warning**: Step had issues

### Relevance Information
```
Step 2: Relevance Check ✅ Passed
  Confidence: 0.85
  Stage: task-action-target
  Explanation: Query contains 'replace' action and 'brake pads' target
```

### Clarification Example
```
📋 Please answer these clarifying questions:

1. What specific issue are you experiencing?
   Your answer: Engine won't start

2. What type of engine do you have?
   Your answer: Diesel
```

### Analysis Results
```
📊 Query Analysis Results:
Query Type: explanation
Semantic Intent: Troubleshooting diesel engine starting issues
Entities: engine, diesel, start

Expanded Queries (3):
  1. Diesel engine won't start troubleshooting
  2. How to fix diesel engine starting problems
  3. Diesel engine cranks but won't start causes
```

## 🧪 Testing Checklist

### Basic Functionality
- [ ] Test with ambiguous query requiring clarification
- [ ] Test with irrelevant query (should be rejected)
- [ ] Test with clear technical query (no clarification needed)
- [ ] Test follow-up queries using context

### Relevance Modes
- [ ] Test two-stage mode with technical terms
- [ ] Test task-action-target with action queries ("remove", "install", "fix")
- [ ] Compare results between modes

### Edge Cases
- [ ] Empty query (just press Enter)
- [ ] Very long query (100+ words)
- [ ] Non-English query
- [ ] Query with special characters

### Session Management
- [ ] Use 'summary' command after several queries
- [ ] Use 'reset' to start fresh
- [ ] Test context preservation across queries

## 🐛 Troubleshooting

### "Ollama connection error"
```bash
# Make sure Ollama is running
ollama serve

# In another terminal, verify model
ollama list
```

### "Import error" or "Module not found"
```bash
# Install dependencies
pip install langchain-ollama colorama

# Or use full requirements
pip install -r requirements-query-analysis.txt
```

### "Clarification not working"
- Make sure you enabled clarification during setup
- Try more ambiguous queries like "fix it", "not working", "help"

## 💡 Pro Tips

1. **For best clarification testing**, use vague queries:
   - "It's broken"
   - "Performance issue"
   - "Something's wrong"

2. **For relevance testing**, mix technical and non-technical:
   - Technical: "adjust carburetor idle speed"
   - Non-technical: "best pizza recipe"

3. **For context testing**, use pronouns in follow-ups:
   - First: "How does a turbocharger work?"
   - Second: "What are its main components?"

4. **View session summary** periodically to see:
   - Total queries processed
   - Entities discussed
   - Topics covered
   - Clarifications made

## 📝 Sample Test Session

```
Enter query: fix engine noise
[Watch 5-step flow, answer clarification questions]

Enter query: summary
[Review session statistics]

Enter query: what's for lunch?
[Test rejection]

Enter query: reset
[Start fresh session]

Enter query: quit
[Exit and see final summary]
```

## 🎯 Expected Results

A successful test run should demonstrate:
1. ✅ Relevance checking catches off-topic queries
2. ✅ Clarification improves ambiguous queries
3. ✅ Context carries across related queries
4. ✅ Analysis provides useful expansions and decompositions
5. ✅ Session tracking maintains conversation state

Happy Testing! 🚀
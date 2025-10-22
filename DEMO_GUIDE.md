# 🎮 Demo Guide - Aging Theory Paper Filter

## Quick Start Demo

The easiest way to run the demo is using the provided shell script:

```bash
# Make the script executable and run it
chmod +x run_demo.sh
./run_demo.sh
```

## Demo Options

### Standard Demo (Recommended)
```bash
./run_demo.sh
```
- Processes 5 papers
- Shows detailed results
- Saves results to JSON file

### Quick Demo
```bash
./run_demo.sh --quick
```
- Processes 3 papers
- Faster execution
- Good for testing

### Verbose Demo
```bash
./run_demo.sh --verbose
```
- Processes 5 papers
- Shows detailed processing information
- Includes reasoning for each classification

### Test Mode
```bash
./run_demo.sh --test
```
- Processes 2 papers
- Quiet mode
- Minimal output

## Manual Demo Execution

If you prefer to run the demo manually:

```bash
# Activate virtual environment
source venv/bin/activate

# Run demo with different options
python demo_aging_filter.py                    # Standard (5 papers)
python demo_aging_filter.py --limit 10         # More papers
python demo_aging_filter.py --limit 3 --quiet # Fewer papers, quiet mode
python demo_aging_filter.py --save-results     # Save results to JSON
```

## Expected Demo Results

The demo will show you:

1. **Environment Validation** ✅
   - Virtual environment check
   - API key validation
   - Test database verification

2. **Sample Paper Loading** 📚
   - 5 papers loaded from test database
   - Paper titles and abstracts displayed
   - Relevant aging-theory topics

3. **AI Processing Pipeline** 🤖
   - GPT-4 Mini classification
   - Chain-of-thought reasoning
   - Confidence scoring

4. **Results Analysis** 📊
   - Classification breakdown (valid/doubted/not_valid)
   - Confidence scores
   - Example classifications with reasoning

5. **Performance Metrics** ⚡
   - Processing speed
   - Token usage
   - Cost analysis
   - Scalability projections

## Sample Output

```
🧬 AGING THEORY PAPER FILTER - INTERACTIVE DEMO
================================================================================
🤖 AI-Powered Scientific Literature Classification System
📊 Demonstrating high-throughput paper filtering capabilities
================================================================================

🔹 Environment Validation
------------------------------------------------------------
✅ OpenAI API key configured
✅ Test database found: /home/diana.z/hack/download_papers_pubmed/paper_collection_test/data/papers.db
✅ Test database contains 92 papers
✅ Environment validation passed!

🔹 Loading Sample Papers (Limit: 5)
------------------------------------------------------------
✅ Loaded 5 papers from test database

📄 Paper 1:
   Title: Not wisely but too well: aging as a cost of neuroendocrine activity.
   Abstract: Progressive decline of some neuroendocrine signaling systems has long been assumed to cause age-related physiological impairments and limit life span....
   DOI: 10.1126/sageke.2004.35.pe33

🔹 AI Processing Pipeline
------------------------------------------------------------
🤖 Starting AI classification process...
⚡ Using GPT-4 Mini for efficient processing
🧠 Chain-of-thought reasoning enabled

Processing paper 1/5... ✅ VALID
Processing paper 2/5... ✅ VALID
Processing paper 3/5... ⚠️ DOUBTED
Processing paper 4/5... ✅ VALID
Processing paper 5/5... ✅ VALID

⚡ Processing completed in 12.34 seconds
📊 Total tokens used: 2,847
💰 Total cost: $0.0089
🚀 Average speed: 0.41 papers/second

🔹 Results Analysis
------------------------------------------------------------
📈 Classification Summary:
   ✅ Valid aging-theory papers: 4 (80.0%)
   ⚠️  Doubted papers: 1 (20.0%)
   ❌ Not valid papers: 0 (0.0%)
   📊 Average confidence: 8.2/10

🔹 Performance Metrics
------------------------------------------------------------
⚡ Processing Efficiency:
   📊 Total papers processed: 5
   🔤 Total tokens used: 2,847
   💰 Total cost: $0.0089
   📈 Average cost per paper: $0.0018
   🎯 Success rate: 100.0%

🚀 Scalability Projections:
   💰 Cost for 1,000 papers: ~$1.78
   💰 Cost for 10,000 papers: ~$17.80
   💰 Cost for 100,000 papers: ~$178.00

🎉 Demo completed!
📊 Check the results above and any generated files
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Activated**
   ```bash
   source venv/bin/activate
   ```

2. **Missing API Key**
   ```bash
   # Edit .env file and add your OpenAI API key
   nano .env
   ```

3. **Test Database Not Found**
   - Ensure the test database exists at the specified path
   - Check file permissions

4. **Rate Limit Issues**
   - The system automatically handles rate limits
   - Processing will slow down but continue automatically

### Getting Help

If you encounter issues:

1. Check the environment validation output
2. Verify your API key is correctly set
3. Ensure the test database is accessible
4. Check the logs for detailed error information

## Next Steps

After running the demo successfully:

1. **Explore the Results**: Check the generated JSON file for detailed results
2. **Scale Up**: Try processing more papers by increasing the limit
3. **Customize**: Modify the prompt or processing parameters
4. **Production Use**: Use the main processing script for large-scale operations

## Production Usage

For production-scale processing:

```bash
# Process all unprocessed papers
python src/process_papers_enhanced.py

# Process with custom limits
python src/process_papers_enhanced.py --limit 1000 --workers 5

# Test mode
python src/process_papers_enhanced.py --test
```

The production system includes:
- Parallel processing with multiple workers
- Checkpoint-based progress tracking
- Robust error handling and retry logic
- Comprehensive logging and monitoring
- Cost tracking and optimization

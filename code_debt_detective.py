#!/usr/bin/env python3
"""
Code Debt Detective - AI Agent
A LinkedIn Portfolio Project

Hidden Problem: Developers spend 60%+ time on technical debt but lack systematic 
ways to identify which code changes create future maintenance burdens.

This AI agent analyzes codebases to:
- Predict technical debt accumulation
- Identify high-risk code patterns
- Suggest refactoring priorities
- Track debt trends over time
- Generate executive-friendly reports

Technologies: Python, OpenAI API, AST parsing, Git analysis, Docker
Author: [Your Name]
"""

import asyncio
import ast
import json
import os
import subprocess
import logging
import webbrowser
import http.server
import socketserver
import threading
import shutil
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import re

import openai
from pydantic import BaseModel


# Core Models
class DebtSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CodeSmell:
    file_path: str
    line_number: int
    smell_type: str
    description: str
    severity: DebtSeverity
    suggested_fix: str
    confidence_score: float


@dataclass
class DebtMetric:
    metric_name: str
    current_value: float
    trend: str  # increasing, decreasing, stable
    risk_level: DebtSeverity
    impact_description: str


class DetectiveConfig(BaseModel):
    project_path: str
    exclude_patterns: List[str] = [".git", "__pycache__", "node_modules", ".venv"]
    file_extensions: List[str] = [".py", ".js", ".ts", ".java", ".cpp", ".cs"]
    max_file_size_mb: int = 5
    analysis_depth: str = "standard"  # quick, standard, deep


# Base Classes
class CodeAnalyzer:
    """Base class for code analysis tools"""
    
    def __init__(self, config: DetectiveConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def scan_codebase(self) -> List[CodeSmell]:
        """Scan entire codebase for issues"""
        smells = []
        
        for file_path in self._get_code_files():
            try:
                file_smells = await self._analyze_file(file_path)
                smells.extend(file_smells)
            except Exception as e:
                self.logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return smells
    
    def _get_code_files(self) -> List[Path]:
        """Get all code files to analyze"""
        files = []
        project_path = Path(self.config.project_path).resolve()
        
        if not project_path.exists():
            self.logger.error(f"Project path does not exist: {project_path}")
            return []
        
        for ext in self.config.file_extensions:
            files.extend(project_path.rglob(f"*{ext}"))
        
        # Filter out excluded patterns
        filtered_files = []
        for file_path in files:
            if not any(pattern in str(file_path) for pattern in self.config.exclude_patterns):
                try:
                    if file_path.stat().st_size < self.config.max_file_size_mb * 1024 * 1024:
                        filtered_files.append(file_path)
                except (OSError, PermissionError) as e:
                    self.logger.warning(f"Cannot access file {file_path}: {e}")
        
        return filtered_files
    
    async def _analyze_file(self, file_path: Path) -> List[CodeSmell]:
        """Analyze a single file for code smells"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            smells = []
            
            # Python-specific analysis
            if file_path.suffix == '.py':
                smells.extend(self._analyze_python_file(file_path, content))
            
            # General analysis for all languages
            smells.extend(self._analyze_general_patterns(file_path, content))
            
            return smells
            
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
            return []
    
    def _analyze_python_file(self, file_path: Path, content: str) -> List[CodeSmell]:
        """Python-specific analysis using AST"""
        smells = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Long function detection
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 20:
                        smells.append(CodeSmell(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            smell_type="long_function",
                            description=f"Function '{node.name}' has {len(node.body)} lines (>20)",
                            severity=DebtSeverity.MEDIUM,
                            suggested_fix="Consider breaking into smaller functions",
                            confidence_score=0.8
                        ))
                
                # Too many parameters
                if isinstance(node, ast.FunctionDef):
                    param_count = len(node.args.args)
                    if param_count > 5:
                        smells.append(CodeSmell(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            smell_type="too_many_parameters",
                            description=f"Function '{node.name}' has {param_count} parameters (>5)",
                            severity=DebtSeverity.HIGH,
                            suggested_fix="Use dataclasses or configuration objects",
                            confidence_score=0.9
                        ))
                
                # Deeply nested code
                if isinstance(node, (ast.If, ast.For, ast.While)):
                    depth = self._calculate_nesting_depth(node)
                    if depth > 3:
                        smells.append(CodeSmell(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            smell_type="deep_nesting",
                            description=f"Code block nested {depth} levels deep",
                            severity=DebtSeverity.HIGH,
                            suggested_fix="Extract methods or use early returns",
                            confidence_score=0.7
                        ))
        
        except SyntaxError:
            smells.append(CodeSmell(
                file_path=str(file_path),
                line_number=1,
                smell_type="syntax_error",
                description="File contains syntax errors",
                severity=DebtSeverity.CRITICAL,
                suggested_fix="Fix syntax errors before proceeding",
                confidence_score=1.0
            ))
        
        return smells
    
    def _analyze_general_patterns(self, file_path: Path, content: str) -> List[CodeSmell]:
        """General analysis for any programming language"""
        smells = []
        lines = content.split('\n')
        
        # File too large
        if len(lines) > 500:
            smells.append(CodeSmell(
                file_path=str(file_path),
                line_number=1,
                smell_type="large_file",
                description=f"File has {len(lines)} lines (>500)",
                severity=DebtSeverity.MEDIUM,
                suggested_fix="Consider splitting into multiple files",
                confidence_score=0.8
            ))
        
        # TODO/FIXME/HACK comments
        for i, line in enumerate(lines, 1):
            if re.search(r'TODO|FIXME|HACK|XXX', line, re.IGNORECASE):
                smells.append(CodeSmell(
                    file_path=str(file_path),
                    line_number=i,
                    smell_type="technical_debt_comment",
                    description=f"Technical debt marker: {line.strip()}",
                    severity=DebtSeverity.LOW,
                    suggested_fix="Address the noted issue",
                    confidence_score=0.6
                ))
        
        # Long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                smells.append(CodeSmell(
                    file_path=str(file_path),
                    line_number=i,
                    smell_type="long_line",
                    description=f"Line length: {len(line)} characters (>120)",
                    severity=DebtSeverity.LOW,
                    suggested_fix="Break line or refactor for readability",
                    confidence_score=0.9
                ))
        
        return smells
    
    def _calculate_nesting_depth(self, node, current_depth=0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth


class GitAnalyzer:
    """Analyze Git history for debt patterns"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_debt_trends(self, days: int = 30) -> List[DebtMetric]:
        """Analyze recent commits for debt trends"""
        try:
            # Check if it's a git repository
            if not (self.repo_path / '.git').exists():
                self.logger.warning(f"Not a git repository: {self.repo_path}")
                return []
            
            # Get recent commits
            since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            cmd = ['git', 'log', f'--since={since_date}', '--pretty=format:%H|%an|%ad|%s', '--date=short']
            result = subprocess.run(
                cmd, cwd=str(self.repo_path), 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Git command failed: {result.stderr}")
                return []
            
            if not result.stdout.strip():
                return []
                
            commits = result.stdout.strip().split('\n')
            
            # Analyze commit patterns
            metrics = []
            
            # Check for rushed commits
            commit_frequency = self._analyze_commit_frequency(commits)
            if commit_frequency > 10:
                metrics.append(DebtMetric(
                    metric_name="High Commit Frequency",
                    current_value=commit_frequency,
                    trend="increasing",
                    risk_level=DebtSeverity.MEDIUM,
                    impact_description="Rapid commits may indicate rushed development"
                ))
            
            # Check for debt-related commit messages
            debt_commits = self._count_debt_commits(commits)
            if debt_commits > len(commits) * 0.2:
                metrics.append(DebtMetric(
                    metric_name="Technical Debt Commits",
                    current_value=debt_commits,
                    trend="concerning",
                    risk_level=DebtSeverity.HIGH,
                    impact_description="High ratio of fix/refactor commits suggests accumulating debt"
                ))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Git analysis failed: {e}")
            return []
    
    def _analyze_commit_frequency(self, commits: List[str]) -> float:
        """Calculate average commits per day"""
        if not commits:
            return 0
        
        dates = set()
        for commit in commits:
            if '|' in commit:
                parts = commit.split('|')
                if len(parts) >= 3:
                    dates.add(parts[2])
        
        return len(commits) / max(len(dates), 1)
    
    def _count_debt_commits(self, commits: List[str]) -> int:
        """Count commits related to technical debt"""
        debt_keywords = ['fix', 'refactor', 'cleanup', 'debt', 'hack', 'workaround', 'temp']
        count = 0
        
        for commit in commits:
            if '|' in commit:
                message = commit.split('|')[-1].lower()
                if any(keyword in message for keyword in debt_keywords):
                    count += 1
        
        return count


class DebtReportGenerator:
    """Generate executive-friendly reports"""
    
    def __init__(self, client: openai.AsyncOpenAI):
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def generate_executive_summary(self, smells: List[CodeSmell], metrics: List[DebtMetric]) -> str:
        """Generate executive summary using AI"""
        
        # Aggregate data
        total_issues = len(smells)
        critical_issues = len([s for s in smells if s.severity == DebtSeverity.CRITICAL])
        high_issues = len([s for s in smells if s.severity == DebtSeverity.HIGH])
        
        # Most common smell types
        smell_counts = {}
        for smell in smells:
            smell_counts[smell.smell_type] = smell_counts.get(smell.smell_type, 0) + 1
        
        top_smells = sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Create prompt for AI
        prompt = f"""
        Generate an executive summary for a technical debt analysis report.
        
        Key Data:
        - Total Issues Found: {total_issues}
        - Critical Issues: {critical_issues}
        - High Priority Issues: {high_issues}
        - Top Issue Types: {top_smells}
        - Trends: {[m.metric_name for m in metrics]}
        
        Create a 3-paragraph executive summary that:
        1. Summarizes the current technical debt state
        2. Highlights the biggest risks and their business impact
        3. Provides 3 concrete recommendations with estimated effort
        
        Make it business-friendly but technically accurate.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return f"""
            Technical Debt Analysis Summary
            
            This codebase contains {total_issues} identified issues requiring attention. 
            With {critical_issues} critical and {high_issues} high-priority items, immediate 
            action is recommended to prevent accumulating technical debt.
            
            The most common issues include code complexity, maintainability concerns, and 
            potential reliability risks. These patterns suggest the need for systematic 
            refactoring and improved development practices.
            
            Recommendations: 1) Address all critical issues immediately, 2) Implement 
            automated code quality checks, 3) Schedule regular refactoring sprints to 
            manage debt systematically.
            """
    
    def generate_html_report(self, smells: List[CodeSmell], metrics: List[DebtMetric], 
                           summary: str, project_name: str) -> str:
        """Generate a beautiful HTML report"""
        
        # Calculate statistics
        severity_counts = {s.value: 0 for s in DebtSeverity}
        for smell in smells:
            severity_counts[smell.severity.value] += 1
        
        # Group smells by type
        smell_groups = {}
        for smell in smells:
            if smell.smell_type not in smell_groups:
                smell_groups[smell.smell_type] = []
            smell_groups[smell.smell_type].append(smell)
        
        # Escape HTML in summary
        summary = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        summary = summary.replace('\n', '<br>')
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Debt Detective Report - {project_name}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                h1 {{ color: #2563eb; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }}
                h2 {{ color: #374151; margin-top: 30px; }}
                .summary {{ background: #f3f4f6; padding: 20px; border-radius: 8px; border-left: 4px solid #2563eb; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric-card {{ background: #ffffff; border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; text-align: center; }}
                .critical {{ border-left: 4px solid #ef4444; }}
                .high {{ border-left: 4px solid #f97316; }}
                .medium {{ border-left: 4px solid #eab308; }}
                .low {{ border-left: 4px solid #22c55e; }}
                .smell-group {{ margin: 20px 0; padding: 15px; background: #f9fafb; border-radius: 6px; }}
                .smell-item {{ margin: 10px 0; padding: 10px; background: white; border-radius: 4px; font-size: 14px; }}
                .confidence {{ float: right; font-weight: bold; }}
                .footer {{ margin-top: 40px; text-align: center; color: #6b7280; font-size: 14px; }}
                .file-path {{ font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; font-size: 12px; color: #6b7280; }}
                .no-issues {{ text-align: center; padding: 40px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🕵️ Code Debt Detective Report</h1>
                <p><strong>Project:</strong> {project_name} | <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                
                <div class="summary">
                    <h2>📊 Executive Summary</h2>
                    <p>{summary}</p>
                </div>
                
                <h2>📈 Debt Metrics</h2>
                <div class="metrics">
                    <div class="metric-card critical">
                        <h3>{severity_counts['critical']}</h3>
                        <p>Critical Issues</p>
                    </div>
                    <div class="metric-card high">
                        <h3>{severity_counts['high']}</h3>
                        <p>High Priority</p>
                    </div>
                    <div class="metric-card medium">
                        <h3>{severity_counts['medium']}</h3>
                        <p>Medium Priority</p>
                    </div>
                    <div class="metric-card low">
                        <h3>{severity_counts['low']}</h3>
                        <p>Low Priority</p>
                    </div>
                </div>
        """
        
        if not smell_groups:
            html += """
                <div class="no-issues">
                    <h2>🎉 No Issues Found!</h2>
                    <p>Your codebase appears to be in excellent shape. Keep up the good work!</p>
                </div>
            """
        else:
            html += "<h2>🔍 Detailed Findings</h2>"
            
            # Add smell groups
            for smell_type, group_smells in smell_groups.items():
                html += f"""
                    <div class="smell-group">
                        <h3>{smell_type.replace('_', ' ').title()} ({len(group_smells)} instances)</h3>
                """
                
                for smell in group_smells[:5]:  # Show top 5 per category
                    severity_class = smell.severity.value
                    # Escape HTML in descriptions
                    description = smell.description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    suggested_fix = smell.suggested_fix.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    file_path = smell.file_path.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    html += f"""
                        <div class="smell-item {severity_class}">
                            <div class="file-path">{file_path}:{smell.line_number}</div>
                            <span class="confidence">Confidence: {smell.confidence_score:.0%}</span>
                            <br><strong>{description}</strong>
                            <br><em>Suggestion: {suggested_fix}</em>
                        </div>
                    """
                
                if len(group_smells) > 5:
                    html += f"<p><em>... and {len(group_smells) - 5} more instances</em></p>"
                
                html += "</div>"
        
        html += """
                <div class="footer">
                    <p>🤖 Generated by Code Debt Detective AI Agent | 
                    <a href="https://github.com/yourusername/code-debt-detective">View on GitHub</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def save_report(self, smells: List[CodeSmell], metrics: List[DebtMetric], 
                         project_name: str, output_dir: str = "reports"):
        """Save comprehensive report"""
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate AI summary
        summary = await self.generate_executive_summary(smells, metrics)
        
        # Save HTML report
        html_report = self.generate_html_report(smells, metrics, summary, project_name)
        html_path = output_path / f"debt_report_{timestamp}.html"
        
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            self.logger.info(f"HTML report saved to: {html_path}")
        except Exception as e:
            self.logger.error(f"Failed to save HTML report: {e}")
            raise
        
        # Save JSON data
        json_data = {
            "project_name": project_name,
            "timestamp": timestamp,
            "summary": summary,
            "smells": [asdict(smell) for smell in smells],
            "metrics": [asdict(metric) for metric in metrics]
        }
        
        json_path = output_path / f"debt_data_{timestamp}.json"
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str, ensure_ascii=False)
            self.logger.info(f"JSON data saved to: {json_path}")
        except Exception as e:
            self.logger.error(f"Failed to save JSON data: {e}")
            raise
        
        return str(html_path), str(json_path)


class ReportViewer:
    """Handle report viewing with multiple options"""
    
    def __init__(self, logger):
        self.logger = logger
        self.server = None
        self.server_thread = None
    
    def open_report(self, html_path: str) -> bool:
        """Try multiple methods to open the report"""
        
        print(f"\n🌐 Opening report: {html_path}")
        
        # Method 1: Try Python webbrowser module
        try:
            webbrowser.open(f"file://{html_path}")
            print("✅ Report opened in default browser")
            return True
        except Exception as e:
            self.logger.warning(f"webbrowser.open failed: {e}")
        
        # Method 2: Try system-specific commands
        try:
            import platform
            system = platform.system()
            
            if system == "Linux":
                # Try multiple Linux browsers
                browsers = ["firefox", "google-chrome", "chromium-browser", "chromium", "xdg-open"]
                for browser in browsers:
                    if shutil.which(browser):
                        subprocess.run([browser, html_path], check=False)
                        print(f"✅ Report opened with {browser}")
                        return True
                        
            elif system == "Darwin":  # macOS
                subprocess.run(["open", html_path], check=False)
                print("✅ Report opened with macOS default browser")
                return True
                
            elif system == "Windows":
                os.startfile(html_path)
                print("✅ Report opened with Windows default browser")
                return True
                
        except Exception as e:
            self.logger.warning(f"System browser open failed: {e}")
        
        # Method 3: Start local server
        try:
            port = self.start_local_server(html_path)
            if port:
                print(f"✅ Local server started at http://localhost:{port}")
                print(f"   Open this URL in your browser to view the report")
                return True
        except Exception as e:
            self.logger.warning(f"Local server failed: {e}")
        
        # Method 4: Show file path
        print(f"📁 Report saved to: {html_path}")
        print(f"🔗 You can manually open this file in any browser")
        return False
    
    def start_local_server(self, html_path: str, port: int = 8000) -> Optional[int]:
        """Start a local HTTP server to serve the report"""
        
        # Try different ports if default is busy
        for try_port in range(port, port + 10):
            try:
                reports_dir = Path(html_path).parent
                html_filename = Path(html_path).name
                
                # Custom handler to serve our specific file
                class CustomHandler(http.server.SimpleHTTPRequestHandler):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, directory=str(reports_dir), **kwargs)
                
                self.server = socketserver.TCPServer(("", try_port), CustomHandler)
                
                # Start server in background thread
                self.server_thread = threading.Thread(target=self.server.serve_forever)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                # Try to open in browser
                try:
                    webbrowser.open(f"http://localhost:{try_port}/{html_filename}")
                except:
                    pass
                
                return try_port
                
            except OSError:
                continue  # Port busy, try next one
        
        return None
    
    def stop_server(self):
        """Stop the local server"""
        if self.server:
            self.server.shutdown()
            self.server = None
            print("🛑 Local server stopped")


# Main Detective Agent
class CodeDebtDetective:
    def __init__(self, config: DetectiveConfig, openai_api_key: str):
        self.config = config
        self.analyzer = CodeAnalyzer(config)
        self.git_analyzer = GitAnalyzer(config.project_path)
        
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.report_generator = DebtReportGenerator(self.client)
        
        self.logger = self._setup_logging()
        self.viewer = ReportViewer(self.logger)
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger("CodeDebtDetective")
    
    async def full_analysis(self, project_name: str = None) -> Tuple[str, str]:
        """Run complete code debt analysis"""
        
        if not project_name:
            project_name = Path(self.config.project_path).name
        
        self.logger.info(f"🕵️ Starting debt analysis for {project_name}")
        
        # Step 1: Analyze current code
        self.logger.info("📁 Scanning codebase...")
        smells = await self.analyzer.scan_codebase()
        self.logger.info(f"Found {len(smells)} potential issues")
        
        # Step 2: Analyze Git history  
        self.logger.info("📈 Analyzing Git trends...")
        metrics = await self.git_analyzer.get_debt_trends()
        self.logger.info(f"Identified {len(metrics)} trend metrics")
        
        # Step 3: Generate reports
        self.logger.info("📝 Generating reports...")
        html_path, json_path = await self.report_generator.save_report(
            smells, metrics, project_name
        )
        
        # Step 4: Print summary
        critical_count = len([s for s in smells if s.severity == DebtSeverity.CRITICAL])
        high_count = len([s for s in smells if s.severity == DebtSeverity.HIGH])
        
        print("\n" + "="*60)
        print(f"🎯 ANALYSIS COMPLETE: {project_name}")
        print("="*60)
        print(f"📊 Total Issues Found: {len(smells)}")
        print(f"🚨 Critical Issues: {critical_count}")
        print(f"⚠️  High Priority: {high_count}")
        print(f"📄 HTML Report: {html_path}")
        print(f"📋 Data Export: {json_path}")
        print("="*60)
        
        return html_path, json_path
    
    async def quick_scan(self) -> Dict[str, Any]:
        """Quick health check scan"""
        smells = await self.analyzer.scan_codebase()
        
        summary = {
            "total_issues": len(smells),
            "critical": len([s for s in smells if s.severity == DebtSeverity.CRITICAL]),
            "high": len([s for s in smells if s.severity == DebtSeverity.HIGH]),
            "health_score": self._calculate_health_score(smells)
        }
        
        return summary
    
    def _calculate_health_score(self, smells: List[CodeSmell]) -> int:
        """Calculate overall codebase health score (0-100)"""
        if not smells:
            return 100
        
        # Weight by severity
        penalty = 0
        for smell in smells:
            if smell.severity == DebtSeverity.CRITICAL:
                penalty += 10
            elif smell.severity == DebtSeverity.HIGH:
                penalty += 5
            elif smell.severity == DebtSeverity.MEDIUM:
                penalty += 2
            else:
                penalty += 1
        
        # Calculate score
        score = max(0, 100 - penalty)
        return score


def display_console_report(smells: List[CodeSmell], metrics: List[DebtMetric], project_name: str):
    """Display a detailed report directly in the console"""
    
    print("\n" + "="*80)
    print(f"🕵️ CODE DEBT DETECTIVE REPORT - {project_name}")
    print("="*80)
    
    # Summary statistics
    total_issues = len(smells)
    severity_counts = {s.value: 0 for s in DebtSeverity}
    for smell in smells:
        severity_counts[smell.severity.value] += 1
    
    print(f"\n📊 SUMMARY STATISTICS")
    print(f"   Total Issues: {total_issues}")
    print(f"   🚨 Critical: {severity_counts['critical']}")
    print(f"   ⚠️  High:     {severity_counts['high']}")
    print(f"   📋 Medium:   {severity_counts['medium']}")
    print(f"   ℹ️  Low:      {severity_counts['low']}")
    
    # Health score
    if total_issues == 0:
        health_score = 100
    else:
        penalty = (severity_counts['critical'] * 10 + 
                  severity_counts['high'] * 5 + 
                  severity_counts['medium'] * 2 + 
                  severity_counts['low'] * 1)
        health_score = max(0, 100 - penalty)
    
    print(f"\n🏥 HEALTH SCORE: {health_score}/100")
    if health_score >= 90:
        print("   Status: 🟢 Excellent")
    elif health_score >= 70:
        print("   Status: 🟡 Good")
    elif health_score >= 50:
        print("   Status: 🟠 Needs Attention")
    else:
        print("   Status: 🔴 Critical")
    
    # Group issues by type
    if smells:
        smell_groups = {}
        for smell in smells:
            if smell.smell_type not in smell_groups:
                smell_groups[smell.smell_type] = []
            smell_groups[smell.smell_type].append(smell)
        
        print(f"\n🔍 DETAILED ISSUES")
        print("-" * 80)
        
        for smell_type, group_smells in sorted(smell_groups.items()):
            print(f"\n📌 {smell_type.replace('_', ' ').title()} ({len(group_smells)} instances)")
            
            # Show top 3 most severe issues in this category
            sorted_smells = sorted(group_smells, 
                                 key=lambda x: ["low", "medium", "high", "critical"].index(x.severity.value),
                                 reverse=True)
            
            for i, smell in enumerate(sorted_smells[:3], 1):
                severity_icon = {"critical": "🚨", "high": "⚠️", "medium": "📋", "low": "ℹ️"}
                
                print(f"   {i}. {severity_icon[smell.severity.value]} {smell.description}")
                print(f"      📁 {smell.file_path}:{smell.line_number}")
                print(f"      💡 {smell.suggested_fix}")
                print(f"      🎯 Confidence: {smell.confidence_score:.0%}")
                
            if len(group_smells) > 3:
                print(f"      ... and {len(group_smells) - 3} more instances")
    
    # Git metrics
    if metrics:
        print(f"\n📈 GIT TREND ANALYSIS")
        print("-" * 80)
        for metric in metrics:
            risk_icon = {"critical": "🚨", "high": "⚠️", "medium": "📋", "low": "ℹ️"}
            print(f"   {risk_icon[metric.risk_level.value]} {metric.metric_name}")
            print(f"      {metric.impact_description}")
            print(f"      Current Value: {metric.current_value}")
    
    print(f"\n📝 RECOMMENDATIONS")
    print("-" * 80)
    
    if severity_counts['critical'] > 0:
        print("   1. 🚨 URGENT: Address all critical issues immediately")
        print("      These issues may cause system failures or security vulnerabilities")
    
    if severity_counts['high'] > 0:
        print("   2. ⚠️  HIGH PRIORITY: Schedule refactoring for high-priority issues")
        print("      These issues significantly impact maintainability")
    
    if total_issues > 20:
        print("   3. 🔄 SYSTEMATIC: Implement automated code quality checks")
        print("      Consider tools like pre-commit hooks, linting, and CI/CD quality gates")
    
    if len(smell_groups.get('technical_debt_comment', [])) > 5:
        print("   4. 📝 DEBT TRACKING: Address accumulated TODO/FIXME comments")
        print("      These represent acknowledged but unresolved technical debt")
    
    print("\n" + "="*80)


# CLI Interface
async def main():
    """Interactive CLI for the Code Debt Detective"""
    
    print("🕵️ Code Debt Detective - AI Agent")
    print("==================================")
    print("Analyzes codebases to identify and predict technical debt")
    print()
    
    # Get configuration
    project_path = input("📁 Enter path to your code project: ").strip()
    if not project_path:
        project_path = "."
    
    project_path = Path(project_path).resolve()
    if not project_path.exists():
        print(f"❌ Path not found: {project_path}")
        return
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   Example: export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Configure detective
    config = DetectiveConfig(
        project_path=str(project_path),
        analysis_depth="standard"
    )
    
    detective = CodeDebtDetective(config, api_key)
    
    # Interactive menu
    while True:
        print("\n🎯 What would you like to do?")
        print("1. Full Analysis & HTML Report")
        print("2. Full Analysis & Console Report")
        print("3. Quick Health Check")
        print("4. Git Trend Analysis")
        print("5. Configure Analysis")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        try:
            if choice == "1":
                project_name = input("Project name (optional): ").strip()
                if not project_name:
                    project_name = project_path.name
                    
                html_path, json_path = await detective.full_analysis(project_name)
                
                # Try to open the report
                detective.viewer.open_report(html_path)
                
                input("\nPress Enter to continue...")
                
            elif choice == "2":
                project_name = input("Project name (optional): ").strip()
                if not project_name:
                    project_name = project_path.name
                
                print("\n⏳ Running full analysis...")
                
                # Analyze current code
                smells = await detective.analyzer.scan_codebase()
                
                # Analyze Git history  
                metrics = await detective.git_analyzer.get_debt_trends()
                
                # Display console report
                display_console_report(smells, metrics, project_name)
                
                # Ask if user wants to save HTML report too
                save_html = input("\n💾 Save HTML report too? (y/n): ").strip().lower()
                if save_html in ['y', 'yes']:
                    html_path, json_path = await detective.report_generator.save_report(
                        smells, metrics, project_name
                    )
                    print(f"✅ HTML report saved: {html_path}")
                
                input("\nPress Enter to continue...")
                
            elif choice == "3":
                print("\n⏳ Running quick scan...")
                summary = await detective.quick_scan()
                
                print(f"\n📊 QUICK HEALTH CHECK")
                print("=" * 40)
                print(f"🏥 Health Score: {summary['health_score']}/100")
                print(f"🚨 Critical: {summary['critical']}")
                print(f"⚠️  High: {summary['high']}")
                print(f"📝 Total Issues: {summary['total_issues']}")
                
                if summary['health_score'] < 70:
                    print("⚠️  Recommendation: Run full analysis for detailed insights")
                elif summary['health_score'] >= 90:
                    print("🎉 Great job! Your codebase looks healthy")
                
                input("\nPress Enter to continue...")
                
            elif choice == "4":
                print("\n📈 Analyzing Git trends...")
                metrics = await detective.git_analyzer.get_debt_trends()
                
                if metrics:
                    print(f"\n📈 GIT TREND ANALYSIS")
                    print("=" * 40)
                    for metric in metrics:
                        risk_icons = {"critical": "🚨", "high": "⚠️", "medium": "📋", "low": "ℹ️"}
                        print(f"{risk_icons[metric.risk_level.value]} {metric.metric_name}")
                        print(f"   {metric.impact_description}")
                        print(f"   Value: {metric.current_value}")
                        print()
                else:
                    print("✅ No concerning Git patterns detected")
                    print("   Your development practices look healthy!")
                
                input("\nPress Enter to continue...")
                
            elif choice == "5":
                print("\n⚙️ Current Configuration:")
                print(f"📁 Path: {config.project_path}")
                print(f"🔧 Extensions: {config.file_extensions}")
                print(f"🎚️  Depth: {config.analysis_depth}")
                print(f"📏 Max file size: {config.max_file_size_mb}MB")
                print(f"🚫 Exclude patterns: {config.exclude_patterns}")
                
                # Allow modification
                print("\n🔧 Modify settings:")
                
                new_depth = input("Analysis depth (quick/standard/deep) [current]: ").strip()
                if new_depth in ["quick", "standard", "deep"]:
                    config.analysis_depth = new_depth
                    print(f"✅ Updated analysis depth to: {new_depth}")
                
                new_extensions = input("File extensions (comma-separated) [current]: ").strip()
                if new_extensions:
                    extensions = [ext.strip() for ext in new_extensions.split(',')]
                    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
                    config.file_extensions = extensions
                    print(f"✅ Updated file extensions to: {extensions}")
                
                new_max_size = input("Max file size in MB [current]: ").strip()
                if new_max_size.isdigit():
                    config.max_file_size_mb = int(new_max_size)
                    print(f"✅ Updated max file size to: {new_max_size}MB")
                
                input("\nPress Enter to continue...")
                
            elif choice == "6":
                detective.viewer.stop_server()
                print("👋 Thanks for using Code Debt Detective!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            detective.viewer.stop_server()
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Check dependencies
    try:
        import openai
        import pydantic
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install openai pydantic")
        exit(1)
    
    asyncio.run(main())

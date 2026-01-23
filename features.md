# LynxTrades - Complete Feature Documentation

## Overview

LynxTrades is a comprehensive trading journal application designed for serious traders. It provides tools for logging, analyzing, and improving trading performance across multiple asset classes and account types, with specific focus on prop firm traders.

---

## 🏦 Account Management

### Multi-Account Support
- **Account Types**: Cash, Margin, IRA/Retirement, and Paper Trading accounts
- **Account Categories**: Retail accounts and Prop Firm accounts
- **Currency Support**: Multi-currency accounts (USD, EUR, GBP, JPY, CAD, AUD, CHF, etc.) with automatic symbol display throughout the app
- **Account Colors**: 8 customizable color options for visual distinction
- **Primary Account**: Designate one account as primary for quick access
- **Balance Tracking**: Track initial and current balance with historical entries
- **Account Status**: Active, Inactive, or Closed status management

### Prop Firm Integration
One of LynxTrades' most unique features is comprehensive prop firm account support:

#### Pre-built Prop Firm Presets
- **FTMO (Normal & Aggressive)**: 2-phase challenge with 10%/5% targets
- **The5ers (High Stakes & Bootcamp)**: 2 and 3-phase options
- **TopStep**: 1-phase with trailing drawdown and consistency rules
- **Funded Trader**: Standard 2-phase challenge
- **MyForexFunds**: 2-phase with 12% max drawdown
- **Apex Trader Funding**: 1-phase with trailing drawdown
- **Custom/Other**: Fully customizable for any prop firm

#### Prop Firm Configuration Options
- **Phase Tracking**: Evaluation Phase 1, 2, 3, Funded, or Failed status
- **Account Sizes**: Predefined sizes from $5,000 to $500,000
- **Profit Targets**: Absolute value and percentage targets per phase
- **Drawdown Types**:
  - **Static**: Fixed from initial balance
  - **Trailing**: Trails with highest balance achieved
  - **EOD Trailing**: Trails based on end-of-day balance
- **Daily/Max Loss Limits**: Both absolute and percentage limits
- **Trading Rules**:
  - Minimum trading days requirement
  - Maximum days allowed for challenge completion
  - Consistency rule (best day can't exceed X% of profit)
  - News trading (allowed, restricted, or forbidden)
  - Weekend holding allowance
  - Overnight holding allowance
- **Funded Account Details**:
  - Profit split percentage (e.g., 80/20)
  - Scaling enabled/disabled
  - Scaling target and multiplier

#### Prop Firm Tracking
- Phase start and end dates
- Account reset events with reason tracking
- Reset reasons: Phase complete, Daily DD failure, Max DD failure, Time limit, Rule violation, New challenge, Manual reset

#### Live Prop Firm Dashboard Status
- Real-time profit target progress with percentage tracking
- Live drawdown monitoring (current usage vs limit)
- Trading days counter toward minimum requirement
- Visual progress bars with color-coded status (green/amber/red)
- Phase-aware calculations (only counts trades within current phase)
- Automatic phase date tracking

---

## 📊 Trade Logging

### Supported Asset Classes
LynxTrades supports 6 different asset types, each with specialized fields:

#### 1. Stock Trades
- Symbol, side (long/short), entry/exit prices
- Quantity, commission, and fees
- Stop loss and take profit levels

#### 2. Options Trades
- **Multi-Leg Support**: Trade single legs or complex multi-leg strategies
- **Strategy Presets**: 10+ pre-built strategy templates:
  - Vertical Spreads (Debit/Credit)
  - Iron Condors & Iron Butterflies
  - Calendar & Diagonal Spreads
  - Straddles & Strangles
  - Butterflies & Condors
- **Leg Management**: Individual leg tracking with strike, expiration, side, and contracts
- **Smart Strategy Detection**: Automatically identifies the strategy name based on leg configuration
- **Leg-Level Executions**: Supports entry/exit for individual legs (Pro feature)
- **Net Price Tracking**: Unified net debit/credit tracking for the entire position
- Underlying price at entry/exit

#### 3. Futures Trades
- Contracts traded
- Point value (e.g., $50 for ES)
- Tick value and tick size
- Expiration date

#### 4. Forex Trades
- Lot size tracking
- Unit-based quantity

#### 5. Crypto Trades
- Fractional quantity support
- High precision pricing

#### 6. Commodity Trades
- **Spot Metals**: Gold (XAU/USD), Silver (XAG/USD), Platinum, etc.
- Unit-based quantity tracking
- Twelve Data API integration for price data
- 24/7 market hours support
- Yellow color theme for visual distinction

### Trade Entry Features

#### Multiple Executions (Scaling In/Out)
- Track individual executions within a single trade
- Each execution records: type (entry/exit), date, price, quantity, commission
- Supports complex scaling strategies
- All executions visualized on the price chart

#### Trade Metadata
- **Setups**: Link trades to predefined trading setups (multiple allowed)
- **Tags**: Custom tagging system for categorization
- **Mistakes**: Track trading mistakes associated with each trade
- **Risk Rules**: Document which risk rules were violated or followed
- **Emotions**: Multi-select emotional state tracking:
  - Confident, Neutral, Anxious, Fearful
  - Greedy, Frustrated, Excited, Calm
- **Confidence Level**: Rate trade confidence numerically
- **Notes**: Free-form text notes per trade
- **Screenshots**: Attach chart images to trades (subscription-limited)

#### Risk Management Fields
- Stop Loss price
- Take Profit price
- Risk/Reward Ratio (calculated)
- Target R-Multiple
- Rule Violations tracking
- Pre-trade Checklist completion tracking

#### Trade Status Tracking
- Open or Closed status
- Archive capability for old trades

#### Smart Automation & Customization
- **Smart Symbol Autofill**: Automatically populates trade details (contracts, strike, side) from your last trade on that symbol. Smartly detects and skips expired dates.
- **Auto SL/TP Calculation**: Automatically calculates Stop Loss and Take Profit levels based on your preferences:
  - **Global Defaults**: Set standard % or $ risk per asset class.
  - **Setup-Specific**: Define unique risk parameters per trading setup.
- **Intelligent Form Behavior**:
  - **Smart Overwrite**: Autofill respects manually edited fields (won't overwrite your work).
  - **Instant Sync**: Settings toggles update instantly across the application.

### Trade Display & Navigation
- **Trade Table**: Full-featured data table with sorting and pagination
- **Trade Cards**: Visual card view for quick scanning
- **Column Visibility**: Customize which columns appear in the table
- **Bulk Actions**: Select and act on multiple trades:
  - Bulk delete
- **Trade Duplication**: Clone existing trades for quick entry
- **Advanced Filters**: Filter by any field (see Filtering section)

### AI-Powered CSV Import (Pro)
Import trades from any broker with intelligent parsing:

- **Smart Broker Detection**: Automatically identifies your broker's export format
- **AI Trade Extraction**: Uses AI to parse and map columns to trade fields
- **Duplicate Detection**: Warns about potential duplicate trades before import
- **Multi-Format Support**: Works with various broker export formats

---

## 📉 Trade Price Chart with Real Market Data

### Real Market Data Integration
Each trade displays an **interactive candlestick chart with real market data**:

- **Alpaca API**: Fetches real OHLCV data for US stocks and options (underlying)
- **Twelve Data API**: Fetches real OHLCV data for Forex and Crypto
- **Futures**: Automatic ETF alternative suggestions (e.g., ES → SPY)

### Intelligent Timeframe Auto-Selection
The chart automatically selects the optimal timeframe based on trade duration:

- **8 Timeframe Options**: 1m, 5m, 15m, 30m, 1H, 4H, 1D, 1W
- **Smart Algorithm**: Targets 120-400 candles for optimal viewing
- **Market Hours Awareness**: Accounts for stock market hours (9:30 AM - 4:00 PM ET) vs 24/7 crypto markets
- **User Override**: Manual timeframe selection available

### Trade Execution Visualization
- **Entry Markers**: Blue arrows showing exact entry price and quantity
- **Exit Markers**: Purple arrows showing exact exit price and quantity
- **Multi-Execution Support**: All scaling entries/exits shown for scaled positions
- **Stop Loss Line**: Red dotted horizontal line at stop loss price
- **Take Profit Line**: Green dotted horizontal line at take profit price

### Chart Features
- **Volume Overlay**: Color-coded volume bars (green for up candles, red for down)
- **Zoom & Pan**: Mouse wheel zoom, drag to pan
- **Auto-Fit**: Chart auto-centers on trade entry/exit with smart padding
- **Symbol & Date Label**: Floating overlay showing symbol and date range
- **Hover Volume Display**: Shows volume on crosshair hover
- **Theme Integration**: Automatic light/dark mode styling
- **Responsive Sizing**: ResizeObserver-based auto-fit

### Smart Pre/Post Buffer Calculation
- Calculates appropriate context before entry and after exit
- For intraday trades: ensures no missing overnight gaps
- For multi-day trades: shows proportional context
- Minimum 120 candles always displayed for context

### Simulated Trade Replay
Re-live your trades with an interactive playback experience:

- **Candle-by-Candle Replay**: Watch the market unfold one candle at a time
- **Intra-Candle Simulation**: Smooth tick-by-tick animation within each candle
- **Playback Controls**:
  - Play/Pause button
  - Adjustable speed (0.5x to 4x)
  - Seek bar for jumping to any point
  - Keyboard shortcuts (Space to play/pause)
- **Dynamic Markers**: Entry/exit markers appear as the replay reaches those timestamps
- **Simulated Feed Label**: Clear indicator that replay uses simulated intra-candle data
- **Seamless Transition**: One-click switch between static chart and replay mode

---

## 📔 Journaling System

### Note Types (Folders)
Pre-defined folder structure:
- **Pre-Trade**: Plan your trades before entry
- **Post-Trade**: Reflect on completed trades
- **Daily Journal**: End-of-day reflections

Users can create custom folders with personalized colors.

### Note Templates
Built-in templates for common journal types:

#### Pre-Trade Plan Template
- Trade Thesis section
- Entry Plan (price, size, reason)
- Exit Plan (target, stop, trailing)
- Risk Assessment (R:R ratio, max loss)
- Catalysts expected
- Pre-Trade Checklist

#### Post-Trade Review Template
- Trade Summary
- What Went Right
- What Went Wrong
- Lessons Learned
- Emotional State analysis
- Improvements for next time

#### Daily Journal Template
- Pre-Market Notes (sentiment, levels, ideas)
- Trading Session log
- Post-Market Review (P&L, observations)
- Lessons Learned

### Note Features
- **Rich Text Editor**: Full-featured editor with:
  - Text styles (bold, italic, underline, strikethrough)
  - Headings (H1-H3)
  - Lists (bulleted and numbered)
  - Links with dialog editor
  - Toolbar with formatting options
  - Timestamp button
- **Multi-Trade Linking**: Link a single note to multiple trades
- **Pin Notes**: Pin important notes for quick access
- **Media Attachments**: Add images and videos (with subscription limits)
- **Cross-Linking**: Link notes to setups, risk rules, and mistakes
- **Content Merging**: When linking trades, content/screenshots merge intelligently
- **Default Folder**: Set a default folder for new notes
- **Filtering**: Filter by folder, tags, date range, linked items, trade outcome

---

## 📈 Analytics & Performance

### Core Trading Metrics
- Net P&L and Gross P&L
- Win Rate percentage
- Profit Factor (gross profit / gross loss)
- Expectancy per trade
- Average Win and Average Loss
- Largest Win and Largest Loss
- Win/Loss Ratio
- Consecutive Wins/Losses streaks
- Average Holding Time
- Average R-Multiple
- Total trade count (wins, losses, breakeven)
- Total commissions paid

### Risk Metrics
- Maximum Drawdown ($ and %)
- **Sharpe Ratio**: Risk-adjusted return
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return to max drawdown
- Recovery Factor
- Return on Capital

### Time-Based Analysis
- **Hourly Performance**: P&L by hour of day (0-23)
- **Day of Week Performance**: Performance by weekday
- **Monthly Performance**: Month-over-month tracking
- Win rate and trade count for each time period

### Analytics Components (17+ specialized views)

#### Performance Analysis
- **Performance Metrics**: Core performance dashboard with all key metrics
- **Equity Curve**: Visual equity growth over time with drawdown overlay
- **Drawdown Chart**: Dedicated drawdown visualization
- **Cumulative P&L Chart**: Running total P&L visualization
- **Monthly Performance Chart**: Month-by-month bar chart

#### Symbol & Market Analysis
- **Symbol Analysis**: Performance breakdown by ticker
- **Top Performers**: Best and worst performing symbols on dashboard

#### Strategy Analysis
- **Setup Analysis**: Win rate and P&L by trading setup with detailed breakdowns
- **Asset Analysis**: Multi-asset performance breakdown
  - Supports Stocks, Options, Futures, Forex, Crypto, Commodities
  - Tabbed view for isolating asset class performance
  - Long vs Short breakdown (Calls vs Puts for Options)
  - ROI and R-Multiple metrics
  - Top Ticker performance per asset class

#### Behavioral Analysis
- **Emotion Analysis**: Performance correlated with emotional states
- **Mistake Analysis**: Impact of mistakes on P&L with frequency tracking
- **Rule Compliance Analysis**: How rule violations affect performance

#### Time Analysis
- **Time Analysis**: Hourly, daily, monthly performance breakdowns
- **Trading Insights**: Pattern recognition and suggestions

#### Journal Analysis
- **Journal Insights**: Correlate journaling habits with performance

#### Goals & Comparisons
- **Goals Tracking**: Set and track trading goals
- **Comparison Tools**: Compare performance between periods

#### Reports
- **Reports**: Generate comprehensive trading reports
- **Report Document**: Full exportable report with charts and metrics

### Customizable Analytics Dashboard
- **Layout Engine**: Configurable widget layout system with drag-and-drop reordering
- **Widget System**: Add/remove analytics widgets
- **Analytics Customizer**: Configure which metrics to display
- **Lazy Loading**: Components load on-demand for performance

---

## 📅 Calendar Views

### Multiple View Modes
- **Year Heatmap**: GitHub-style heatmap showing daily P&L intensity
- **Month View**: Traditional monthly calendar with trade summaries
- **Week View**: Weekly overview of trading activity
- **Day View**: Detailed view of individual trading day with all trades

### Calendar Features
- Color-coded cells based on P&L (green for profits, red for losses)
- Trade count per day
- Quick navigation between periods
- Click-through to trade details
- P&L summary per cell

---

## ⚠️ Risk Management

### Risk Rules (8 Auto-Tracked Types)

1. **Max Daily Trades**: Limit trades per day (e.g., max 3 trades/day)
2. **Max Weekly Trades**: Limit trades per week
3. **Max Daily Loss**: Stop trading when daily loss exceeds limit ($)
4. **Max Weekly Loss**: Weekly loss cap
5. **Max Open Positions**: Limit concurrent positions
6. **Trading Hours**: Only trade within specific hours (time range with start/end)
7. **Max Position Size**: Maximum dollar value per position
8. **Max Trades Per Symbol**: Limit trades per ticker per day
9. **Custom Rules**: Personal reminders/guidelines (not auto-tracked)

### Rule Configuration
- Name and description
- Color coding (15 color options)
- Value with unit (currency, percent, count, ratio)
- Time range for trading hours rules
- Active/inactive status
- Auto-tracking for structured rule types

### Risk Profile Management
- Account size tracking
- Risk per trade percentage
- Maximum daily loss setting
- Pre-trade checklist items (customizable list)

### Position Sizing Calculator
- Calculate position size based on:
  - Account size
  - Entry price
  - Stop loss price
  - Risk percentage or fixed amount
- Output: shares, planned risk, R-multiple, position value
- Buying power shortfall detection

---

## 🎯 Trading Setups

### Setup Definition
- **Name** and **Description**
- **Entry Conditions**: Customizable list of criteria for trade entry
- **Exit Conditions**: Customizable list of criteria for trade exit
- **Timeframes** (8 options): 1m, 5m, 15m, 30m, 1H, 4H, Daily, Weekly
- **Markets**: Which asset classes this setup applies to (stocks, options, futures, forex, crypto)
- **Color**: Visual identification (8 colors)

### Setup Tracking
- Automatically calculated win rate from linked trades
- Average profit per trade
- Total trade count using this setup
- Performance metrics over time

### Setup Validation on Trade Detail
When viewing a trade linked to a setup:
- **Timeframe Matching**: Green chip if trade duration matches setup timeframe, amber warning if mismatch
- **Market Matching**: Highlights which market types match the trade's asset class
- **Entry/Exit Condition Checklists**: Toggle checkboxes for each condition (persisted)

---

## ❌ Mistake Tracking

### Mistake Categories (9 types)
1. **Entry Mistake**: Wrong entry timing or type
2. **Exit Mistake**: Poor exit decision
3. **Position Sizing**: Incorrect size for trade
4. **Wrong Timing**: Bad market timing
5. **Emotional Decision**: Fear, greed, FOMO, revenge
6. **Rule Violation**: Broke trading rules
7. **Technical Error**: Chart misreading
8. **Trade Management**: Poor stop/target management
9. **Other**: Miscellaneous

### Mistake Severity Levels
- **Low** (Blue): Minor impact
- **Medium** (Amber): Noticeable impact
- **High** (Orange): Significant impact
- **Critical** (Red): Major trading error

### Mistake Features
- Impact estimation in dollars
- Frequency tracking (occurrence count)
- Prevention tips (user-defined list, displayed on trade detail)
- Linked trade history
- Color coding for quick identification
- Description field for context

---

## 🏷️ Tagging System

### Tag Configuration
- Custom name
- Description (optional)
- Color selection (15 colors):
  - Gray, Red, Orange, Amber, Yellow
  - Lime, Green, Emerald, Teal, Cyan
  - Blue, Indigo, Violet, Purple, Pink
- Usage count tracking

### Tag Applications
- Apply to trades for categorization
- Filter trades by tag
- Analyze performance by tag
- Cross-reference in notes

---

## 🔍 Global Search & Filtering

### Global Search Categories
- **Navigation**: Search pages/sections
- **Actions**: Quick commands with keyboard shortcuts
- **Trades**: Search trade history
- **Setups**: Find trading setups
- **Tags**: Search tags
- **Mistakes**: Find mistake patterns
- **Accounts**: Account search
- **Notes**: Search journal entries

### Trade Search
Full-text search across **10+ trade fields**:
- Symbol
- Side (long/short)
- Entry & Exit Price
- Status
- Setups (by name)
- Risks (by name)
- Mistakes (by name)
- Tags (by name)
- Confidence level
- Emotion

### Advanced Trade Filtering
- **Asset Type**: Stocks, Options, Futures, Forex, Crypto, Commodity
- **Side**: Long, Short, Call, Put
- **Status**: Open, Closed
- **Result**: Win, Loss, Breakeven
- **Date Range**: Calendar picker with dual-month view
- **P&L Range**: Min and max P&L filters
- **Tags**: Multi-select tag filter
- Active filter count indicator
- One-click filter clearing

### Saved Filter Presets
- **Save Current Filters**: Name and save any filter combination
- **Load Saved Filters**: One-click to apply saved presets
- **Set Default**: Mark a filter as default (auto-loads)
- **Delete Presets**: Remove saved filters
- **Dropdown Variant**: Compact dropdown for tight spaces
- **LocalStorage Persistence**: Filters persist across sessions

---

## 📊 Charts & Visualization

### Chart Types (14 specialized charts)
1. **Area Chart**: Filled line charts for trends
2. **Bar Chart**: Comparative bar visualizations
3. **Line Chart**: Simple line plots
4. **Pie Chart**: Distribution visualization
5. **Candlestick Chart**: OHLC price data with LightweightCharts
6. **Equity Curve**: Portfolio value over time with drawdown overlay
7. **Drawdown Chart**: Visualize drawdown periods
8. **Heatmap Chart**: Intensity-based data display
9. **Financial Chart**: Full-featured price charts
10. **Volume Chart**: Trading volume visualization
11. **Trade Markers**: Entry/exit markers on charts
12. **Cumulative P&L Chart**: Running total visualization
13. **Monthly Performance Chart**: Bar chart by month
14. **Base Chart**: Configurable base component

### Chart Features
- Responsive design with ResizeObserver
- Interactive tooltips
- Legend customization
- Theme integration (light/dark)
- Configurable axes and grids
- Zoom and pan support
- Framer Motion animations

---

## 🎨 Customization & Settings

### Appearance Settings
- **Theme**: Light, Dark, or System preference

### User Preferences
- Default account selection
- Currency preference
- Timezone configuration
- Date format selection

### Dashboard Customization
- Add/remove dashboard widgets
- Layout persistence per user

### Keyboard Shortcuts
- Enable/disable global shortcuts
- Vim mode for rich text editors
- Quick action hotkeys

---

## 💾 Data Management

### Export Capabilities
- **CSV Trade Export**: Full trade data export with:
  - Core trade details (date, time, symbol, type, side)
  - Entry/exit data
  - Risk management fields (SL, TP, Target R)
  - Performance metrics (P&L, percentages, result)
  - Linked setups, tags, mistakes (resolved to human-readable names)
  - Options-specific fields (strike, expiration)
  - Emotions and confidence levels

### Data Actions
- Account deletion with cascading data cleanup
- Delete all trades for a user with media cleanup

---

## Trade Detail View

### Trade Info Panel
Tabbed panel showing contextual information:

#### Risk Rule Checklist Tab
- Displays user-defined checklist items
- Shows which items were checked before the trade
- Green checkmarks for completed items

#### Setups Tab
- Shows linked setup name with color chip
- **Timeframe Validation**: Green chip if trade duration matches, amber warning if mismatch
- **Market Validation**: Highlights matching asset classes
- Entry conditions with completion status
- Exit conditions with completion status

#### Mistakes Tab
- Shows linked mistake name with color chip
- Severity badge (Low/Medium/High/Critical)
- Description text
- **Prevention Tips**: Displayed as bullet list for learning

### Trade Stats Grid
- Entry/Exit prices
- P&L (gross and net)
- Holding time
- R-Multiple
- Commission and fees

### Trade Journal Section
- Linked notes display
- Trade notes field


---

## 🔐 Authentication & Security

### Auth Methods
- Email/Password registration
- Google Sign-In integration
- Password reset via email
- Email verification

### Security Features
- Firebase Authentication
- Re-authentication for sensitive actions (account deletion, password change)
- Secure password requirements

### User Profile
- Display name customization
- Avatar/profile photo
- Account creation date tracking
- Last login tracking

---

## 💳 Subscription Tiers

### Free Tier ($0 forever)
- Unlimited trade entries & journaling
- Full analytics suite access
- Unlimited strategy playbooks (setups)
- Up to 2 trading accounts
- 50 MB storage
- Reports tool & data export

### Pro Tier ($8/month)
- Everything in Free, plus:
- Unlimited trading accounts
- AI-powered CSV import
- 1 GB storage (20x more)
- High-res uploads (10MB limit per file)
- More screenshots per trade
- Priority support

### Subscription Features
- Plan management
- Billing period tracking
- Storage usage monitoring (bytes)
- Upgrade/downgrade flows
- Stripe integration

---

## 🚀 Onboarding Experience

### Onboarding Flow
1. **Welcome**: Introduction to LynxTrades
2. **Account Setup**: Create first trading account (retail or prop firm)
3. **Complete**: Ready to start trading

### Product Tour
Interactive tour with 5 guided steps:
1. Sidebar navigation introduction
2. Dashboard overview explanation
3. Add trade functionality
4. Analytics features
5. Risk management tools

### Tour Features
- Highlight targets with CSS selectors
- Configurable positions (top, bottom, left, right, center)
- Optional interaction blocking
- Progress tracking
- Skip capability

### First-Time User Experience
- Default collections seeded on first login:
  - Sample setup (generic trading strategy)
  - Sample risk rule (max daily trades)
  - Default folders for notes
  - Default templates for journaling

---

## 📱 Dashboard

### Dashboard Widgets (13 components)
1. **Overview Cards**: Key metrics (P&L, Win Rate, Profit Factor, Trade Count) with trend indicators
2. **Prop Firm Status Header**: Challenge progress for prop firm accounts (profit target %, drawdown %, trading days)
3. **Quick Stats**: Fast performance summary
4. **Performance Widgets**: Detailed equity curve and metrics
5. **Mini Calendar**: Compact heatmap calendar view
6. **Open Positions**: Current open trades list
7. **Recent Trades**: Latest completed trades
8. **Recent Notes**: Latest journal entries
9. **Top Performers**: Best performing symbols with P&L and win rate
10. **Risk Overview**: Risk rule compliance status

### Dashboard Features
- **Drag & Drop Layout**: Reorder widgets with drag handles
- **Customizable Widgets**: Show/hide widgets via settings
- **Collapsible Containers**: Minimize widgets to save space
- Real-time data updates
- Account filter (view by account or all)
- Date range filter (today, 7d, 30d, 90d, YTD, custom, all)

---

## 📝 Landing Page

### Marketing Components
- **Hero Section**: Animated entrance with interactive dashboard mockup
- **Features Section**: Comprehensive feature showcase
- **Pricing**: Tier comparison table
- **FAQ**: Common questions answered
- **CTA**: Call-to-action sections

### Design Features
- Framer Motion animations
- Magnetic button effects
- Responsive design
- 3D perspective effects on dashboard mockup
- Mobile-optimized layout

---

## 🔧 Technical Architecture

### Frontend Stack
- React with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Zustand for state management
- React Router for navigation
- LightweightCharts for financial charts
- Framer Motion for animations
- React Hook Form for forms
- Zod for validation

### Backend & Infrastructure
- Firebase Authentication
- Firestore Database
- Firebase Storage
- Cloud Functions for serverless logic
- Vercel deployment

### External APIs
- **Alpaca Markets API**: US stock and options price data
- **Twelve Data API**: Forex and cryptocurrency price data
- **Stripe**: Subscription billing

### Code Organization
- Feature-based module structure (`src/features/`)
- Shared component library (`src/components/`)
- Type-safe API layer (`src/api/`)
- Custom hooks for business logic
- Service layer for data operations
- Store layer with Zustand for state
- Lazy loading for analytics components

---

## 🌟 What Makes LynxTrades Unique

1. **Simulated Trade Replay**: Watch your trades unfold in real-time with animated candle-by-candle playback - a premium feature for reviewing entries and exits

2. **Real Market Data Charts**: Every trade displays actual OHLCV data from Alpaca/Twelve Data with entry/exit markers, SL/TP lines, and intelligent timeframe selection

3. **Prop Firm First**: Deep integration with prop firm challenges, including 8 presets for major firms and comprehensive rule/drawdown tracking

4. **Multi-Currency Support**: Track trades in multiple currencies with automatic conversion for unified P&L reporting

5. **Advanced Options Strategies**: Deep support for multi-leg strategies with automatic recognition, 10+ presets, and granular leg-level tracking

6. **Multi-Asset Support**: True support for Stocks, Options, Futures, Forex, Crypto, and Commodities - not just stocks

7. **Risk-Centric Design**: 8 auto-tracked risk rule types plus pre-trade checklists with real-time compliance monitoring

8. **Setup Performance**: Track which strategies actually work with automatic win rate and P&L attribution

9. **Behavioral Analysis**: Track emotions, mistakes, and rule violations with prevention tips to improve trading psychology

10. **Flexible Journaling**: Rich text editor with templates, multi-trade linking, content merging, and media attachments

11. **Calendar Heatmap**: GitHub-style visualization of trading performance over time with 5 intensity levels

12. **Execution Tracking**: Support for scaling in/out with individual execution logging and visualization

13. **Setup Validation**: Setups validate timeframe and market type against actual trade data with visual feedback

14. **AI-Powered Import**: Upload CSV exports from any broker and AI automatically maps and imports your trades

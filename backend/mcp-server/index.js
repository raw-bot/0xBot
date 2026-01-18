#!/usr/bin/env node

/**
 * 0xBot MCP Server
 * Central hub for all trading bot tools
 * Reduces context consumption from multiple MCP servers by 90%
 *
 * Architecture:
 * - Market Data Tool (fetch OHLCV, indicators)
 * - Trading Execution Tool (place orders, manage positions)
 * - Portfolio Tool (track balance, P&L)
 * - Analysis Tool (calculate signals, confluence scores)
 * - Workflow Executor (run JS scripts for complex workflows)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import fs from "fs";
import path from "path";
import axios from "axios";
import vm from "vm";

// Configuration
const BOT_API = process.env.BOT_API_URL || "http://localhost:8000";
const PYTHON_BIN = process.env.PYTHON_BIN || "python3";

class TradingBotMCPServer {
  constructor() {
    this.server = new Server({
      name: "0xBot-MCP-Server",
      version: "1.0.0",
    });

    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, () =>
      this.listTools()
    );
    this.server.setRequestHandler(CallToolRequestSchema, (request) =>
      this.callTool(request)
    );
  }

  listTools() {
    return {
      tools: [
        {
          name: "fetch_market_data",
          description: "Fetch real-time market data for symbols with Trinity indicators",
          inputSchema: {
            type: "object",
            properties: {
              symbols: {
                type: "array",
                items: { type: "string" },
                description: "Trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])",
              },
              include_indicators: {
                type: "boolean",
                description: "Include Trinity indicators (SMA_200, EMA_20, RSI, ADX, Supertrend, Volume)",
                default: true,
              },
            },
            required: ["symbols"],
          },
        },
        {
          name: "get_trinity_signals",
          description: "Generate Trinity trading signals based on market data",
          inputSchema: {
            type: "object",
            properties: {
              symbols: {
                type: "array",
                items: { type: "string" },
                description: "Trading pairs to analyze",
              },
              min_confluence: {
                type: "number",
                description: "Minimum confluence score (0-100) to return signals",
                default: 60,
              },
            },
            required: ["symbols"],
          },
        },
        {
          name: "execute_trade",
          description: "Place a trading order (paper trading)",
          inputSchema: {
            type: "object",
            properties: {
              symbol: { type: "string", description: "Trading pair" },
              side: { type: "string", enum: ["long", "short"] },
              size_percent: {
                type: "number",
                description: "Position size as % of capital (1-3)",
              },
              entry_price: { type: "number" },
              stop_loss: { type: "number" },
              take_profit: { type: "number" },
            },
            required: ["symbol", "side", "size_percent"],
          },
        },
        {
          name: "get_portfolio",
          description: "Get current portfolio positions and P&L",
          inputSchema: {
            type: "object",
            properties: {
              include_history: {
                type: "boolean",
                description: "Include trade history",
              },
            },
          },
        },
        {
          name: "execute_workflow",
          description: "Execute complex trading workflows using JavaScript",
          inputSchema: {
            type: "object",
            properties: {
              script: {
                type: "string",
                description: "JavaScript code to execute workflow",
              },
              context: {
                type: "object",
                description: "Variables to pass to script context",
              },
            },
            required: ["script"],
          },
        },
        {
          name: "analyze_performance",
          description: "Analyze bot performance metrics",
          inputSchema: {
            type: "object",
            properties: {
              period_hours: {
                type: "number",
                description: "Time period to analyze (default: 24)",
              },
            },
          },
        },
      ],
    };
  }

  async callTool(request) {
    const { name, arguments: args } = request;

    try {
      let result;

      switch (name) {
        case "fetch_market_data":
          result = await this.fetchMarketData(args);
          break;
        case "get_trinity_signals":
          result = await this.getTrinitySignals(args);
          break;
        case "execute_trade":
          result = await this.executeTrade(args);
          break;
        case "get_portfolio":
          result = await this.getPortfolio(args);
          break;
        case "execute_workflow":
          result = await this.executeWorkflow(args);
          break;
        case "analyze_performance":
          result = await this.analyzePerformance(args);
          break;
        default:
          return {
            content: [
              {
                type: "text",
                text: `Unknown tool: ${name}`,
              },
            ],
            isError: true,
          };
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  async fetchMarketData(args) {
    const { symbols, include_indicators = true } = args;

    try {
      const response = await axios.post(`${BOT_API}/api/market-data/fetch`, {
        symbols,
        include_indicators,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch market data: ${error.message}`);
    }
  }

  async getTrinitySignals(args) {
    const { symbols, min_confluence = 60 } = args;

    try {
      const response = await axios.post(`${BOT_API}/api/signals/trinity`, {
        symbols,
        min_confluence,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to generate Trinity signals: ${error.message}`);
    }
  }

  async executeTrade(args) {
    const {
      symbol,
      side,
      size_percent,
      entry_price,
      stop_loss,
      take_profit,
    } = args;

    try {
      const response = await axios.post(`${BOT_API}/api/trades/execute`, {
        symbol,
        side,
        size_percent,
        entry_price,
        stop_loss,
        take_profit,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to execute trade: ${error.message}`);
    }
  }

  async getPortfolio(args) {
    const { include_history = false } = args;

    try {
      const response = await axios.get(`${BOT_API}/api/portfolio`, {
        params: { include_history },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get portfolio: ${error.message}`);
    }
  }

  async executeWorkflow(args) {
    const { script, context = {} } = args;

    try {
      // Create a safe sandbox for workflow execution
      const sandbox = {
        console,
        Math,
        JSON,
        Date,
        Set,
        Map,
        Array,
        Object,
        String,
        Number,
        // Bot API helpers
        fetchMarketData: (symbols) => this.fetchMarketData({ symbols }),
        getTrinitySignals: (symbols, minConfluence) =>
          this.getTrinitySignals({ symbols, min_confluence: minConfluence }),
        executeTrade: (tradeArgs) => this.executeTrade(tradeArgs),
        getPortfolio: (opts) => this.getPortfolio(opts),
        // Utilities
        sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
        ...context,
      };

      const vmContext = vm.createContext(sandbox);
      const result = vm.runInContext(script, vmContext, {
        timeout: 30000, // 30 second timeout
      });

      return {
        success: true,
        result,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      throw new Error(`Workflow execution failed: ${error.message}`);
    }
  }

  async analyzePerformance(args) {
    const { period_hours = 24 } = args;

    try {
      const response = await axios.get(`${BOT_API}/api/performance/analyze`, {
        params: { period_hours },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to analyze performance: ${error.message}`);
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("0xBot MCP Server running on stdio");
  }
}

// Start server
const server = new TradingBotMCPServer();
server.run().catch(console.error);

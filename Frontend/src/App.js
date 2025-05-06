import React, { useState, useEffect, useRef, useCallback, useMemo, useLayoutEffect } from 'react';
import {
  Box,
  TextField,
  Paper,
  Typography,
  Avatar,
  IconButton,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Menu,
  MenuItem,
  useMediaQuery,
  GlobalStyles,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import SettingsIcon from '@mui/icons-material/Settings';
import PaletteIcon from '@mui/icons-material/Palette';
import ContrastIcon from '@mui/icons-material/Contrast';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import NightsStayIcon from '@mui/icons-material/NightsStay';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import BrightnessHighIcon from '@mui/icons-material/BrightnessHigh';
import FilterVintageIcon from '@mui/icons-material/FilterVintage';
import { styled, alpha } from '@mui/system';
import { v4 as uuidv4 } from 'uuid';

// Import logo images
const zahraLogo = '/mir logo final-3.jpg';
const dahabLogo = '/mir logo final-2.jpg';
const laylaLogo = '/mir logo final-1.jpg';
const fayrouzLogo = '/mir logo final-4.jpg';

// Logo mapping for each theme
const themeLogos = {
  zahra: zahraLogo,
  dahab: dahabLogo,
  layla: laylaLogo,
  fayrouz: fayrouzLogo,
};

/**
 * ========== CLIENT IDENTIFICATION ==========
 * We generate or retrieve a unique client ID for this session, which helps the backend
 * maintain conversation history with this specific client. Using localStorage ensures
 * the same client ID persists across page refreshes, providing continuity in the chat.
 */
const CLIENT_ID = localStorage.getItem('chatClientId') || uuidv4();
localStorage.setItem('chatClientId', CLIENT_ID);

/**
 * WebSocket endpoint URL construction
 * Format: ws://server-address:port/path/client-id
 * The client-id is appended to the URL path, which allows the server
 * to identify this client when establishing the WebSocket connection.
 */
const WS_ENDPOINT = `ws://localhost:8000/ws/${CLIENT_ID}`;

/**
 * ========== TEXT FORMATTING UTILITY ==========
 * This utility function processes message text and converts markdown-like syntax to styled elements.
 * Two main features:
 * 1. Converts "**text**" patterns to bold text with theme-based styling
 * 2. Specially handles numbered titles in format "1. **Title:**" to maintain both number and title styling
 * 
 * The implementation uses regex patterns and string splitting to identify formatting markers,
 * then replaces them with properly styled React elements.
 */
const formatMessageText = (text, theme) => {
  if (!text) return '';
  
  // First handle numbered titles with double asterisks (e.g., "1. **كلمي نفسك بحنية:**")
  // This regex pattern looks for: digit(s) + dot + space + **text**
  const numberedTitleRegex = /(\d+\.\s)(\*\*.*?\*\*)/g;
  let processed = text;
  
  // Replace numbered titles with styled components
  processed = processed.replace(numberedTitleRegex, (match, numberedPart, boldPart) => {
    // Extract the text without ** from the bold part
    const boldText = boldPart.slice(2, -2);
    
    // Return a span with the entire sequence (number + bold text) styled
    // We use a uniqueKey to avoid React warning about keys
    const uniqueKey = `title-${Math.random().toString(36).substring(2, 9)}`;
    
    return `<styled-title key="${uniqueKey}" numbered="${numberedPart}" bold="${boldText}">`;
  });
  
  // Then handle any remaining ** patterns (without numbers)
  const segments = processed.split(/(\*\*.*?\*\*)|(<styled-title.*?>)/g).filter(Boolean);
  
  return segments.map((segment, index) => {
    // Check if this is a styled title we created above
    if (segment.startsWith('<styled-title')) {
      // Extract the numbered part and bold text using regex
      const numberedMatch = segment.match(/numbered="(.*?)"/);
      const boldMatch = segment.match(/bold="(.*?)"/);
      
      if (numberedMatch && boldMatch) {
        const numberedPart = numberedMatch[1];
        const boldText = boldMatch[1];
        
        // Return a styled span with both parts
        return (
          <strong
            key={`title-${index}`}
            style={{
              color: theme.palette.primary.main,
              fontWeight: 'bold',
              display: 'block', // Optional: makes titles block elements for better separation
              marginTop: '0.5em', // Optional: adds some spacing above titles
            }}
          >
            {numberedPart}{boldText}
          </strong>
        );
      }
      return segment; // Fallback
    }
    
    // Handle regular ** patterns as before
    if (segment.startsWith('**') && segment.endsWith('**')) {
      const boldText = segment.slice(2, -2);
      return (
        <strong
          key={index}
          style={{
            color: theme.palette.primary.main,
            fontWeight: 'bold',
          }}
        >
          {boldText}
        </strong>
      );
    }
    
    // Return regular text segments as-is
    return segment;
  });
};

/**
 * ========== THEMING SYSTEM ==========
 * Material UI allows creating custom themes that define colors, typography,
 * spacing, and other design elements used across the app.
 * 
 * First, we define base options for all themes:
 * - RTL text direction for Arabic
 * - Cairo font family
 * - Common border radius and font weights
 */
const baseThemeOptions = {
  direction: 'rtl',
  typography: {
    fontFamily: 'Cairo, Roboto, Arial',
    h4: { fontWeight: 'bold' },
    h6: { fontWeight: 600 },
    body1: { lineHeight: 1.7 },
  },
  shape: {
    borderRadius: 12,
  },
};

/**
 * Define multiple themes that users can switch between:
 * - zahra: Light theme with pink/feminine colors
 * - dahab: Warm gold/amber theme
 * - layla: Dark theme with purple accents
 * - fayrouz: Turquoise/teal theme
 * 
 * Each theme defines:
 * - mode: 'light' or 'dark'
 * - primary/secondary colors
 * - background colors
 * - text colors
 * - message bubble colors for user and bot
 */
const themes = {
  zahra: createTheme({
    ...baseThemeOptions,
    palette: {
      mode: 'light',
      primary: { main: '#7ebcbc' },
      secondary: { main: '#7ebcbc' },
      background: { default: '#7ebcbc ', paper: '#7ebcbc' },   
      text: { primary: '#100f0d', secondary: '#ffffff' },
      userMessage: '#ffffff',
      botMessage: '#ffffff',
      
    },
  }),
  dahab: createTheme({
    ...baseThemeOptions,
    palette: {
      mode: 'light',
      primary: { main: '#488a94' },      
      secondary: { main: '#d3c69c' },     
      background: { 
        default: '#7ebcbc',               
        paper: '#488a94'                
      },
      text: { 
        primary: '#100f0d',           
        secondary: '#488a94'              
      },
      userMessage: '#ffffff',            
      botMessage: '#ffffff',             
      accent: '#d4af37'                  
    },
  }),
  layla: createTheme({
    ...baseThemeOptions,
    palette: {
      mode: 'dark',
      primary: { main: '#d3c69c' },
      secondary: { main: '#7ebcbc' },
      background: { default: '#d3c69c', paper: '#d3c69c' },
      text: { primary: '#100f0d', secondary: '#ffffff' },
      userMessage: '#ffffff',
      botMessage: '#ffffff',
    },
  }),
  fayrouz: createTheme({
    ...baseThemeOptions,
    palette: {
      mode: 'light',
      primary: { main: '#d3c69c' },
      secondary: { main: '#d3c69c' },
      background: { default: '#baae7f', paper: '#d3c69c' },
      text: { primary: '#ffffff', secondary: '#ffffff' },
      userMessage: '#d3c69c',
      botMessage: '#d3c69c',
      messageText: '#ffffff',
    },
  }),
};

/**
 * ========== STYLED COMPONENTS ==========
 * Material UI's styled API creates pre-styled components that apply consistent
 * styling based on the current theme. These create the chat interface elements.
 */

/**
 * ChatContainer: The main chat interface box
 * - Uses Paper component for card-like elevation with shadow
 * - Flexbox layout with column direction
 * - Fixed height calculation with vh units and a max-height
 * - Uses theme.shape.borderRadius for consistent rounded corners
 */
const ChatContainer = styled(Paper)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: 'calc(100vh - 120px)',
  maxHeight: '800px',
  boxShadow: `0 5px 15px ${alpha(theme.palette.text.primary, 0.1)}`,
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
  width: '120%',
  marginTop: theme.spacing(2),
  marginBottom: theme.spacing(2),
}));

/**
 * MessageArea: The scrollable container for chat messages
 * - Uses flexGrow: 1 to take up all available vertical space
 * - Flexbox layout with column direction
 * - Configurable padding based on theme spacing
 * - Background color from theme
 */
const MessageArea = styled(Box)(({ theme }) => ({
  flexGrow: 1,
  padding: theme.spacing(2),
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  backgroundColor: theme.palette.background.default,
}));

/**
 * ChatHeader: The header of the chat interface
 * - Displays the bot's avatar, name, and connection status
 * - Includes a settings button for theme selection
 */
const ChatHeader = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  padding: theme.spacing(1.5, 2),
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  borderTopLeftRadius: theme.shape.borderRadius,
  borderTopRightRadius: theme.shape.borderRadius,
}));

/**
 * InputContainer: The container for the message input field and send button
 * - Fixed at the bottom of the chat interface
 * - Styled to match the theme
 */
const InputContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  padding: theme.spacing(1, 2),
  backgroundColor: theme.palette.background.paper,
  borderTop: `1px solid ${theme.palette.divider}`,
  alignItems: 'center',
}));

/**
 * MessageBubble: The styled container for individual messages
 * - Differentiates between user and bot messages
 * - Applies theme-based colors and alignment
 */
const MessageBubble = styled(Box)(({ type, theme }) => ({
  maxWidth: '75%',
  padding: theme.spacing(1, 1.5),
  borderRadius: '18px',
  marginBottom: theme.spacing(1.5),
  wordBreak: 'break-word',
  overflowWrap: 'break-word',
  fontFamily: 'Cairo, sans-serif',
  alignSelf: type === 'user' ? 'flex-end' : 'flex-start',
  backgroundColor: type === 'user' ? theme.palette.userMessage : theme.palette.botMessage,
  color: theme.palette.messageText || theme.palette.getContrastText(type === 'user' ? theme.palette.userMessage : theme.palette.botMessage),
  boxShadow: `0 1px 2px ${alpha(theme.palette.text.primary, 0.1)}`,
  position: 'relative',
  borderTopLeftRadius: type === 'bot' ? '4px' : '18px',
  borderTopRightRadius: type === 'user' ? '4px' : '18px',
  minHeight: '1.5em',
  animation: 'fadeIn 0.3s ease-in-out',
  width: 'auto',
  clear: type === 'user' ? 'left' : 'right',
}));

/**
 * ========== ANIMATION KEYFRAMES ==========
 * Define CSS animations that will be used for the typing indicator
 * - typingBounce: Animation for the dots in the typing indicator
 * - Dots move up and down with opacity changes for a subtle bounce effect
 */
const typingAnimation = `
@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.6; // Start and end slightly faded
  }
  30% {
    transform: translateY(-4px);
    opacity: 1; // Full opacity at the peak
  }
}
`;

/**
 * BotTypingIndicator: Shows when the bot is typing
 * - Similar to MessageBubble but with special styling
 * - Uses inline-flex for natural sizing based on content
 * - Aligned to the left/start of the container
 */
const BotTypingIndicator = styled(Box)(({ theme }) => ({
  display: 'inline-flex',
  alignItems: 'center',
  alignSelf: 'flex-start',
  backgroundColor: theme.palette.botMessage,
  padding: theme.spacing(1.2, 1.8),
  borderRadius: '18px',
  marginBottom: theme.spacing(1.5),
  boxShadow: `0 1px 2px ${alpha(theme.palette.text.primary, 0.1)}`,
  borderTopLeftRadius: '4px',
  color: alpha(theme.palette.text.primary, 0.7),
}));

/**
 * TypingDot: Individual animated dots in the typing indicator
 * - Small circles that bounce up and down
 * - Uses the theme's primary color for visual consistency
 * - Each dot has a different animation delay for a wave effect
 */
const TypingDot = styled('span')(({ theme, delay }) => ({
  width: '8px',
  height: '8px',
  margin: '0 3px',
  borderRadius: '50%',
  display: 'inline-block',
  backgroundColor: theme.palette.primary.main,
  animation: 'typingBounce 1.4s infinite ease-in-out',
  animationDelay: `${delay}s`,
}));

/**
 * ========== CONSTANTS ==========
 * Application-wide constants for configuration
 */
const STREAM_CHAR_DELAY = 30;
const BACKEND_INACTIVITY_TIMEOUT = 1500;

/**
 * Custom scrollbar styling function
 * Creates a thin, subtle scrollbar that fits the theme
 * Used with GlobalStyles to apply these styles app-wide
 */
const globalScrollbarStyles = (theme) => ({
  '::-webkit-scrollbar': {
    width: '6px',
  },
  '::-webkit-scrollbar-track': {
    background: alpha(theme.palette.text.primary, 0.05),
    borderRadius: '3px',
  },
  '::-webkit-scrollbar-thumb': {
    background: alpha(theme.palette.text.primary, 0.3),
    borderRadius: '3px',
  },
  '::-webkit-scrollbar-thumb:hover': {
    background: alpha(theme.palette.text.primary, 0.5),
  },
});

/**
 * ========== MAIN APP COMPONENT ==========
 */
function App() {
  /**
   * ========== STATE MANAGEMENT ==========
   * Using React's useState hook to maintain component state
   */
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  
  /**
   * ========== REFS ==========
   * React refs provide a way to access DOM elements directly
   * and persist values between renders without causing re-renders
   */
  const messagesEndRef = useRef(null);
  const backendTimeoutRef = useRef(null);
  const streamingMessageIdRef = useRef(null);
  const charQueueRef = useRef([]);
  const isStreamingCharsRef = useRef(false);
  const streamTimeoutRef = useRef(null);
  
  const isMobile = useMediaQuery('(max-width:600px)');

  /**
   * ========== THEME MANAGEMENT ==========
   * Handle theme selection and persistence
   */
  const [currentThemeKey, setCurrentThemeKey] = useState(() => {
    return localStorage.getItem('chatTheme') || 'zahra';
  });
  const theme = useMemo(() => themes[currentThemeKey] || themes.zahra, [currentThemeKey]);

  /**
   * ========== SETTINGS MENU ==========
   * State and handlers for the settings dropdown menu
   */
  const [anchorEl, setAnchorEl] = useState(null);
  const openSettings = Boolean(anchorEl);

  const handleSettingsClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleSettingsClose = () => {
    setAnchorEl(null);
  };

  const handleThemeChange = (themeKey) => {
    setCurrentThemeKey(themeKey);
    localStorage.setItem('chatTheme', themeKey);
    handleSettingsClose();
  };

  /**
   * ========== AUTO-SCROLLING ==========
   * Automatically scroll to the bottom when new messages arrive
   * Uses useLayoutEffect to ensure scrolling happens before browser painting
   */
  useLayoutEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages]);

  /**
   * ========== TEXT STREAMING ==========
   * Streams text one character at a time for a typewriter effect
   */
  const streamNextCharacter = useCallback(() => {
    if (charQueueRef.current.length === 0 || !streamingMessageIdRef.current) {
      isStreamingCharsRef.current = false;
      return;
    }

    isStreamingCharsRef.current = true;
    const char = charQueueRef.current.shift();
    const currentStreamingId = streamingMessageIdRef.current;

    setMessages(prevMessages =>
      prevMessages.map(msg =>
        msg.id === currentStreamingId ? { ...msg, text: msg.text + char } : msg
      )
    );

    streamTimeoutRef.current = setTimeout(streamNextCharacter, STREAM_CHAR_DELAY);
  }, []);

  /**
   * ========== WEBSOCKET CONNECTION ==========
   * Establishes and maintains WebSocket connection to the backend
   */
  useEffect(() => {
    console.log("Attempting to connect WebSocket...");
    const ws = new WebSocket(WS_ENDPOINT);
    let reconnectTimer = null;

    const connectWebSocket = () => {
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close();
      }
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (backendTimeoutRef.current) clearTimeout(backendTimeoutRef.current);
      if (streamTimeoutRef.current) clearTimeout(streamTimeoutRef.current);
      streamingMessageIdRef.current = null;
      charQueueRef.current = [];
      isStreamingCharsRef.current = false;
      backendTimeoutRef.current = null;

      const newWs = new WebSocket(WS_ENDPOINT);

      newWs.onopen = () => {
        console.log('Connected to WebSocket server');
        setConnected(true);
        setSocket(newWs);
        if (reconnectTimer) clearTimeout(reconnectTimer);
      };

      newWs.onmessage = (event) => {
        const responseChunk = event.data;

        charQueueRef.current.push(...responseChunk.split(''));

        if (!isStreamingCharsRef.current && streamingMessageIdRef.current) {
          streamNextCharacter();
        }

        if (backendTimeoutRef.current) {
          clearTimeout(backendTimeoutRef.current);
        }

        backendTimeoutRef.current = setTimeout(() => {
          const finalizeStream = () => {
            if (charQueueRef.current.length === 0 && !isStreamingCharsRef.current) {
              const finalStreamingId = streamingMessageIdRef.current;
              if (finalStreamingId) {
                setMessages(prevMessages => prevMessages.map(msg =>
                  msg.id === finalStreamingId ? { ...msg, streaming: false } : msg
                ));
              }
              streamingMessageIdRef.current = null;
              backendTimeoutRef.current = null;
            } else {
              setTimeout(finalizeStream, STREAM_CHAR_DELAY * 5);
            }
          };
          finalizeStream();
        }, BACKEND_INACTIVITY_TIMEOUT);
      };

      newWs.onclose = () => {
        console.log('Disconnected from WebSocket server');
        setConnected(false);
        setSocket(null);
        if (streamingMessageIdRef.current) {
          const finalStreamingId = streamingMessageIdRef.current;
          setMessages(prevMessages => prevMessages.map(msg =>
            msg.id === finalStreamingId ? { ...msg, streaming: false } : msg
          ));
          streamingMessageIdRef.current = null;
        }
        if (backendTimeoutRef.current) clearTimeout(backendTimeoutRef.current);
        if (streamTimeoutRef.current) clearTimeout(streamTimeoutRef.current);
        charQueueRef.current = [];
        isStreamingCharsRef.current = false;
        backendTimeoutRef.current = null;

        reconnectTimer = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connectWebSocket();
        }, 5000);
      };

      newWs.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (streamingMessageIdRef.current) {
          const finalStreamingId = streamingMessageIdRef.current;
          setMessages(prevMessages => prevMessages.map(msg =>
            msg.id === finalStreamingId ? { ...msg, streaming: false } : msg
          ));
          streamingMessageIdRef.current = null;
        }
        if (backendTimeoutRef.current) clearTimeout(backendTimeoutRef.current);
        if (streamTimeoutRef.current) clearTimeout(streamTimeoutRef.current);
        charQueueRef.current = [];
        isStreamingCharsRef.current = false;
        backendTimeoutRef.current = null;
      };
    };

    connectWebSocket();

    return () => {
      console.log("Cleaning up WebSocket connection.");
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
      setConnected(false);
      if (backendTimeoutRef.current) clearTimeout(backendTimeoutRef.current);
      if (streamTimeoutRef.current) clearTimeout(streamTimeoutRef.current);
      streamingMessageIdRef.current = null;
      charQueueRef.current = [];
      isStreamingCharsRef.current = false;
      backendTimeoutRef.current = null;
    };
  }, []);

  /**
   * ========== MESSAGE SENDING ==========
   * Handles sending messages to the backend and updating UI
   */
  const sendMessage = (messageText = input) => {
    const textToSend = messageText.trim();
    if (textToSend && connected && socket) {
      if (streamTimeoutRef.current) clearTimeout(streamTimeoutRef.current);
      charQueueRef.current = [];
      isStreamingCharsRef.current = false;

      if (streamingMessageIdRef.current) {
        const finalStreamingId = streamingMessageIdRef.current;
        setMessages(prevMessages => prevMessages.map(msg =>
          (msg.id === finalStreamingId && msg.streaming !== false) ? { ...msg, streaming: false } : msg
        ));
        streamingMessageIdRef.current = null;
      }
      
      if (backendTimeoutRef.current) {
        clearTimeout(backendTimeoutRef.current);
        backendTimeoutRef.current = null;
      }

      const userMessageId = uuidv4();
      const botMessageId = uuidv4();

      setMessages(prev => [
        ...prev, 
        { id: userMessageId, sender: 'user', text: textToSend },
        { id: botMessageId, sender: 'bot', text: '', streaming: true }
      ]);

      socket.send(textToSend);
      setInput('');
      
      streamingMessageIdRef.current = botMessageId;
    }
  };

  /**
   * Handle Enter key in the input field
   * Sends the message when Enter is pressed (without Shift)
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /**
   * Check if we should show the typing indicator
   * True if there's a streaming message with empty text
   */
  const showSpinner = messages.some(m => m.id === streamingMessageIdRef.current && m.streaming && m.text === '');

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <GlobalStyles styles={theme => ({
        ...globalScrollbarStyles(theme),
        [typingAnimation]: {},
      })} />
      <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          p: isMobile ? 0 : 2,
          bgcolor: 'background.default',
          minHeight: '100vh',
          width: '100%',
          boxSizing: 'border-box',
      }}>
        <Box sx={{ width: '100%', maxWidth: 'md', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Box
            component="img"
            src={themeLogos[currentThemeKey]}
            alt="مير - داعمك اليومي"
            sx={{
              height: 'auto',
              maxWidth: '100%',
              mt: 2,
              mb: 1,
              maxHeight: '100px',
              width: 'auto',
              minWidth: '200px',
              objectFit: 'contain'
            }}
          />

          <ChatContainer>
            <ChatHeader>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar 
                  src={themeLogos[currentThemeKey]}
                  sx={{ 
                    width: 40, 
                    height: 40, 
                    mr: 1.5,
                    bgcolor: 'transparent'
                  }}
                />
                <Box>
                  <Typography variant="h6" component="div" sx={{ color: '#ffffff' }}>
                    مير
                  </Typography>
                  <Typography variant="caption" component="div" sx={{ color: '#ffffff', opacity: 0.8 }}>
                    {connected ? 'متصلة وجاهزة للمساعدة' : 'جاري الاتصال...'}
                  </Typography>
                </Box>
              </Box>
              <IconButton
                color="inherit"
                aria-label="settings"
                aria-controls={openSettings ? 'settings-menu' : undefined}
                aria-haspopup="true"
                aria-expanded={openSettings ? 'true' : undefined}
                onClick={handleSettingsClick}
                sx={{ color: '#ffffff' }}
              >
                <SettingsIcon />
              </IconButton>
              <Menu
                id="settings-menu"
                anchorEl={anchorEl}
                open={openSettings}
                onClose={handleSettingsClose}
                MenuListProps={{ 'aria-labelledby': 'settings-button' }}
              >
                <MenuItem disabled>
                  <PaletteIcon sx={{ mr: 1, opacity: 0.7 }} /> اختيار السمة:
                </MenuItem>
                <MenuItem onClick={() => handleThemeChange('zahra')}>
                  <LocalFloristIcon sx={{ mr: 1, color: themes.zahra.palette.primary.main }} /> زهرة (مشرق)
                </MenuItem>
                <MenuItem onClick={() => handleThemeChange('dahab')}>
                  <BrightnessHighIcon sx={{ mr: 1, color: themes.dahab.palette.primary.main }} /> ذهب (دافئ)
                </MenuItem>
                <MenuItem onClick={() => handleThemeChange('layla')}>
                  <NightsStayIcon sx={{ mr: 1, color: themes.layla.palette.primary.main }} /> ليلى (داكن)
                </MenuItem>
                <MenuItem onClick={() => handleThemeChange('fayrouz')}>
                  <FilterVintageIcon sx={{ mr: 1, color: themes.fayrouz.palette.primary.main }} /> فيروز (هادئ)
                </MenuItem>
              </Menu>
            </ChatHeader>

            <MessageArea>
              {messages.length === 0 && !showSpinner && (
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  p: 3,
                  opacity: 0.9
                }}>
                  <SupportAgentIcon sx={{ fontSize: 50, color: 'primary.main', mb: 2 }} />
                  <Typography variant="body1" sx={{ mb: 2, color: '#ffffff' }}>
                     ازاي أقدر أساعدك النهاردة؟
                  </Typography>
                </Box>
              )}

              <Box sx={{ 
                display: 'flex',
                flexDirection: 'column',
                width: '100%'
              }}>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} type={msg.sender}>
                    <Typography 
                      variant="body1" 
                      component="div" 
                      dir="auto" 
                      sx={{ color: 'inherit', whiteSpace: 'pre-wrap' }}
                    >
                      {msg.sender === 'bot' ? formatMessageText(msg.text, theme) : msg.text}
                      {msg.sender === 'bot' && msg.streaming === true && (
                        <span style={{ animation: 'blink 1s step-end infinite', marginLeft: '2px', opacity: 0.7 }}>|</span>
                      )}
                    </Typography>
                  </MessageBubble>
                ))}
              </Box>

              {showSpinner && (
                <BotTypingIndicator>
                  <TypingDot delay={0} />
                  <TypingDot delay={0.2} />
                  <TypingDot delay={0.4} />
                </BotTypingIndicator>
              )}

              <div ref={messagesEndRef} style={{ height: '1px', clear: 'both' }} />
            </MessageArea>

            <InputContainer>
              <TextField
                fullWidth
                placeholder="اكتبي رسالتك هنا..."
                variant="outlined"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                sx={{
                  mr: 1,
                  '& .MuiOutlinedInput-root': {
                    borderRadius: '25px',
                    backgroundColor: theme.palette.mode === 'dark' ? alpha(theme.palette.common.white, 0.1) : alpha(theme.palette.common.black, 0.05),
                    '& fieldset': {
                      borderColor: 'transparent',
                    },
                    '&:hover fieldset': {
                      borderColor: theme.palette.primary.light,
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: theme.palette.primary.main,
                    },
                  },
                  '& .MuiInputBase-input::placeholder': {
                    color: theme.palette.text.secondary,
                    opacity: 0.8,
                  },
                }}
                disabled={!connected}
                multiline
                maxRows={4}
              />
              <IconButton
                color="primary"
                onClick={() => sendMessage()}
                disabled={!connected || !input.trim()}
                sx={{
                  backgroundColor: theme.palette.primary.main,
                  color: theme.palette.primary.contrastText,
                  '&:hover': {
                    backgroundColor: theme.palette.primary.dark,
                  },
                  '&.Mui-disabled': {
                    backgroundColor: alpha(theme.palette.text.primary, 0.12),
                    color: alpha(theme.palette.text.primary, 0.26)
                  },
                  width: 48,
                  height: 48,
                }}
              >
                <SendIcon sx={{ transform: theme.direction === 'rtl' ? 'rotate(180deg)' : 'none' }} />
              </IconButton>
            </InputContainer>
          </ChatContainer>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;

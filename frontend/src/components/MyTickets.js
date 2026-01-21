import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Breadcrumbs,
  Link
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  Assignment as TicketIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  CheckCircle
} from '@mui/icons-material';

const MyTickets = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [showTicketDialog, setShowTicketDialog] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [approvalComments, setApprovalComments] = useState('');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    // Check URL parameter for tab selection
    const tab = searchParams.get('tab');
    if (tab === 'approvals') {
      setTabValue(1);
    } else {
      setTabValue(0);
    }
  }, [searchParams]);

  useEffect(() => {
    fetchTickets();
    fetchApprovals();
  }, []);

  const fetchTickets = async () => {
    try {
      const token = localStorage.getItem('token');
      console.log('Fetching tickets with token:', token ? 'Token exists' : 'No token');
      
      const response = await fetch('http://localhost:8002/tickets/?my_tickets=true', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Tickets response status:', response.status);
      const data = await response.json();
      console.log('Tickets data received:', data);
      setTickets(data);
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchApprovals = async () => {
    try {
      const token = localStorage.getItem('token');
      console.log('Fetching approvals with token:', token ? 'Token exists' : 'No token');
      
      const response = await fetch('http://localhost:8002/approvals/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Approvals response status:', response.status);
      const data = await response.json();
      console.log('Approvals data received:', data);
      setApprovals(data);
    } catch (error) {
      console.error('Error fetching approvals:', error);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'draft': 'default',
      'submitted': 'info',
      'pending_approval': 'warning',
      'approved': 'success',
      'rejected': 'error',
      'in_progress': 'primary',
      'resolved': 'success',
      'closed': 'default',
      'cancelled': 'error'
    };
    return colors[status] || 'default';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      'low': 'success',
      'medium': 'warning',
      'high': 'error',
      'critical': 'error'
    };
    return colors[priority] || 'default';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleViewTicket = (ticket) => {
    setSelectedTicket(ticket);
    setShowTicketDialog(true);
  };

  const handleApproval = (approval) => {
    setSelectedApproval(approval);
    setApprovalComments('');
    setShowApprovalDialog(true);
  };

  const submitApproval = async (status) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/approvals/${selectedApproval.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          status: status,
          comments: approvalComments
        })
      });

      if (response.ok) {
        setShowApprovalDialog(false);
        fetchApprovals();
        fetchTickets(); // Refresh tickets to show updated status
        alert(`Approval ${status} successfully!`);
      } else {
        throw new Error('Failed to update approval');
      }
    } catch (error) {
      console.error('Error updating approval:', error);
      alert('Error updating approval. Please try again.');
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography>Loading tickets...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {/* Header */}
      <Box sx={{ p: 3, backgroundColor: 'white', borderBottom: '1px solid #dee2e6' }}>
        <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 2 }}>
          <Link 
            color="inherit" 
            href="#" 
            onClick={(e) => { e.preventDefault(); navigate('/'); }}
            sx={{ textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
          >
            Home
          </Link>
          <Typography color="text.primary">My Tickets</Typography>
        </Breadcrumbs>
        
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h4" sx={{ color: '#333', fontWeight: 600 }}>
            My Tickets & Approvals
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => { fetchTickets(); fetchApprovals(); }}
            sx={{ borderColor: '#FF8C42', color: '#FF8C42' }}
          >
            Refresh
          </Button>
        </Box>
        
        <Typography variant="body1" color="text.secondary">
          Track your submitted tickets and manage approval requests
        </Typography>
      </Box>

      <Box sx={{ p: 3 }}>
        {/* Summary Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <TicketIcon sx={{ fontSize: 40, color: '#FF8C42', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#333' }}>
                  {tickets.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Tickets
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <TicketIcon sx={{ fontSize: 40, color: '#8B1538', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#333' }}>
                  {tickets.filter(t => ['submitted', 'pending_approval', 'approved', 'in_progress'].includes(t.status)).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Open Tickets
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <ApproveIcon sx={{ fontSize: 40, color: '#4CAF50', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#333' }}>
                  {approvals.filter(a => a.status === 'pending').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Pending Approvals
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <CheckCircle sx={{ fontSize: 40, color: '#2196F3', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#333' }}>
                  {tickets.filter(t => ['resolved', 'closed'].includes(t.status)).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Resolved Tickets
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label={`My Tickets (${tickets.length})`} />
            <Tab label={`My Approvals (${approvals.length})`} />
          </Tabs>
        </Paper>

        {/* My Tickets Tab */}
        {tabValue === 0 && (
          <Paper>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell><strong>Ticket #</strong></TableCell>
                    <TableCell><strong>Title</strong></TableCell>
                    <TableCell><strong>Type</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                    <TableCell><strong>Priority</strong></TableCell>
                    <TableCell><strong>Created</strong></TableCell>
                    <TableCell><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tickets.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4 }}>
                        <Typography color="text.secondary">
                          No tickets found. Create your first ticket from the homepage.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tickets.map((ticket) => (
                      <TableRow key={ticket.id} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', color: '#8B1538' }}>
                            {ticket.ticket_number}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {ticket.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={ticket.ticket_type.replace('_', ' ')} 
                            size="small" 
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={ticket.status.replace('_', ' ')} 
                            size="small" 
                            color={getStatusColor(ticket.status)}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={ticket.priority} 
                            size="small" 
                            color={getPriorityColor(ticket.priority)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(ticket.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="View Details">
                            <IconButton 
                              size="small" 
                              onClick={() => handleViewTicket(ticket)}
                              sx={{ color: '#FF8C42' }}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* My Approvals Tab */}
        {tabValue === 1 && (
          <Paper>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell><strong>Ticket</strong></TableCell>
                    <TableCell><strong>Requester</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                    <TableCell><strong>Requested</strong></TableCell>
                    <TableCell><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {approvals.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} sx={{ textAlign: 'center', py: 4 }}>
                        <Typography color="text.secondary">
                          No approval requests found.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    approvals.map((approval) => (
                      <TableRow key={approval.id} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {approval.ticket_title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {approval.requester_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={approval.status} 
                            size="small" 
                            color={getStatusColor(approval.status)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(approval.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {approval.status === 'pending' ? (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleApproval(approval)}
                              sx={{ borderColor: '#FF8C42', color: '#FF8C42' }}
                            >
                              Review
                            </Button>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              {approval.status === 'approved' ? 'Approved' : 'Rejected'}
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}
      </Box>

      {/* Ticket Detail Dialog */}
      <Dialog 
        open={showTicketDialog} 
        onClose={() => setShowTicketDialog(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedTicket && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h6">
                  Ticket {selectedTicket.ticket_number}
                </Typography>
                <Chip 
                  label={selectedTicket.status.replace('_', ' ')} 
                  color={getStatusColor(selectedTicket.status)}
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">Title</Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>{selectedTicket.title}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">Type</Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>{selectedTicket.ticket_type.replace('_', ' ')}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">Priority</Typography>
                  <Chip label={selectedTicket.priority} size="small" color={getPriorityColor(selectedTicket.priority)} />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">Created</Typography>
                  <Typography variant="body1">{formatDate(selectedTicket.created_at)}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="text.secondary">Description</Typography>
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedTicket.description}
                  </Typography>
                </Grid>
                {selectedTicket.resolution_notes && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" color="text.secondary">Resolution Notes</Typography>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {selectedTicket.resolution_notes}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setShowTicketDialog(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Approval Dialog */}
      <Dialog 
        open={showApprovalDialog} 
        onClose={() => setShowApprovalDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        {selectedApproval && (
          <>
            <DialogTitle>
              Approval Request
            </DialogTitle>
            <DialogContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                {selectedApproval.ticket_title}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Requested by: {selectedApproval.requester_name}
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Comments (optional)"
                value={approvalComments}
                onChange={(e) => setApprovalComments(e.target.value)}
                sx={{ mt: 2 }}
              />
            </DialogContent>
            <DialogActions>
              <Button 
                onClick={() => setShowApprovalDialog(false)}
                color="inherit"
              >
                Cancel
              </Button>
              <Button 
                onClick={() => submitApproval('rejected')}
                color="error"
                startIcon={<RejectIcon />}
              >
                Reject
              </Button>
              <Button 
                onClick={() => submitApproval('approved')}
                color="success"
                startIcon={<ApproveIcon />}
                variant="contained"
              >
                Approve
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default MyTickets;
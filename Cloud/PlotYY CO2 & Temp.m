% MATLAB code for visualizing data from a channel as a filled area
% 2D plot using the THINGSPEAKAREA function.

% Prior to running this MATLAB code template, assign the channel ID to read
% data from to the 'readChannelID' variable. Also, assign the field IDs
% within the channel that you want to read data from to 'fieldID1', and
% 'fieldID2'. 

% TODO - Replace the [] with channel ID to read data from:
readChannelID = [PUT HERE CHANNEL];
% TODO - Replace the [] with the Field ID to read data from:
fieldID1 = 1;
% TODO - Replace the [] with the Field ID to read data from:
fieldID2 = 2;

% Channel Read API Key 
% If your channel is private, then enter the read API
% Key between the '' below: 
readAPIKey = 'PUT HERE READ API KEY';

%% Read Data %%
NumPoints = 600;

% Read first data variable
[CO2,time] = thingSpeakRead(readChannelID, 'Field', fieldID1, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

% Read second data variable
Temp = thingSpeakRead(readChannelID, 'Field', fieldID2, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

%% Process Data %%


%% Visualize Data %%
% Learn more about the THINGSPEAKPLOT function by going to the Documentation tab on
% the right side pane of this page.
thingSpeakPlotYY(time, CO2, time , Temp,'YLabel2','Temperature','YLabel1','CO2');
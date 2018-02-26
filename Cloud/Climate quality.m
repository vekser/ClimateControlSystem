% Template MATLAB code for visualizing correlated data using the
% THINGSPEAKSCATTER function.

% Prior to running this MATLAB code template, assign the channel ID to read
% data from to the 'readChannelID' variable. Also, assign the field IDs
% within the channel that you want to read data from to 'fieldID1', and
% 'fieldID2'. 

% TODO - Replace the [] with channel ID to read data from:
readChannelID = [PUT HERE CHANNEL];

% Channel Read API Key 
% If your channel is private, then enter the read API
% Key between the '' below: 
readAPIKey = 'PUT HERE READ API KEY';


% TODO - Replace the [] with the Field ID to read data from:
fieldID1 = [1];
% TODO - Replace the [] with the Field ID to read data from:
fieldID2 = [2];

%%-----------------------------------------------------------

%% Read Data %%
NumPoints = 600;

% Read first data variable
[CO2,time] = thingSpeakRead(readChannelID, 'Field', fieldID1, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

% Read second data variable
Temp = thingSpeakRead(readChannelID, 'Field', fieldID2, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

%% Processing
%CO2
CO2 (CO2 < 400) = 400;
CO2 (CO2 > 2000) = 2000;
CQ_CO2 = (CO2 - 400)/1600;

coef = 3;
CQ_CO2 = exp(CQ_CO2*coef)/exp(coef);
%Temp
CQ_Temp=abs(Temp-23)/10;
CQ_Temp(CQ_Temp>1)=1;



%% Visualize Data %%

w1=1.0;
w2=0.1;

CQ = 5*(1-(CQ_CO2 * w1 + CQ_Temp*w2)/(w1+w2));
CQ = round(CQ,3);

thingSpeakPlot(time,CQ,'Grid','on','XLabel','Time','YLabel','Climate quality')


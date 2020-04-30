export function cssData(user) {
var css =`

*
	{
	box-sizing: border-box;
	}


.status, .info
	{
	display: flex;
	flex-wrap: wrap;
	justify-content: space-around;
	padding: 8px 16px;
	}

.ibox
	{
	flex: 1 1 auto;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	align-items: center;
	width: 100px;
	height: 70px;
	padding: 3px;
	margin-bottom: 16px;
  color: #808080;
	}

button 
	{
	display: inline-block;
	max-width: 125px;
	min-width: 70px;
	height: 36px;
	margin-bottom: 16px;
	padding: 1px 6px;
	border-radius: 4px;
	border: 1px solid var(--primary-color);
  border-image: initial;
	background-color: var(--lovelace-background);
	font-family: var(--ha-card-header-font-family, inherit);
  font-size: var(--ha-card-header-font-size, 18px);
	}
	
button:focus
	{
	outline: 0px;
	}	 
	

.c_title 
	{
	color: var(--ha-card-header-color, --primary-text-color);
	font-family: var(--ha-card-header-font-family, inherit);
	font-size: var(--ha-card-header-font-size, 24px);
	letter-spacing: -0.012em;
	line-height: 32px;
	padding: 24px 16px 16px;
	}
	
.c_icon
	{
	position: absolute;
	top: 0;
	right: 0;
	z-index: 25;
	opacity: 0.6
	}
	
.sep
  {
	width: 100%;
	height: 1px;
	background-image: linear-gradient(to right, transparent, transparent, var(--primary-color), transparent, transparent);
	}

.mtxt
	{
	font-family: var(--ha-card-header-font-family, inherit);
	font-size: 1.2em;
	}
	
p.mtxt, .ibox > p
	{
	margin: 3px;
	}
	
.itxt
	{
	width: 105px;
	overflow: hidden;
	}
	
	
.ON, .true
	{
	color: var(--primary-color);
	font-weight: bold;
	}
	
.OFF, .false
	{
	color: #808080;
	}
.g
	{
	color: green;
	}
.err
	{
	color: red;
	}
  
  
`
return css;
}
